import datetime
import os
import logging
from ipaddress import IPv4Network as network_object_v4, IPv6Network as network_object_v6
from tinydb import TinyDB, Query
from .tinydb_transaction_isolated_storage import transaction_isolated_storage
from tinydb.middlewares import CachingMiddleware

'''
'''
class scope():
    '''
    string representation of object instance
    '''
    def __str__(self):
        return(str.format(
            "{}|allocated={}",
            self.get_network_object(),
            self.is_allocated() ) )

    '''
    Gets a db instance that utilizes a single file
    '''
    @staticmethod
    def get_db():
        return(TinyDB(str.format(
            "/data/v4.json"
        ), storage = CachingMiddleware ) )

    '''
    Gets a db instance that utilizes it's own file unique to this scope instance,
    this is the default method of storage used by the scope class if no database
    object is specified for the constructor parameter
    '''
    def get_instance_db(self):
        return(TinyDB(str.format(
            "/data/{}.{}.json",
            self.network_address_to_big_number(),
            self.get_prefix()
        ), storage = transaction_isolated_storage ) )

    '''
    Converts IP address to a big number (int fits all python, technically a ulong or ulonglong for ipv6)
    '''
    def network_address_to_big_number(self):
        return(int.from_bytes(
            self.get_network_object(
            ).network_address.packed, 'big') )

    '''
    Converts an unsigned long long or unsigned long (TCP/IP 6 vs 4) number to
    an IP address, network endianness (big)

    Notes:
    argument is bytes, packed
    ex:
    addr = scope.big_number_to_network_address(int(
    id
    ).to_bytes(16, 'big'))

    16 =  size of longlong, but the zero bits are not counted by bit_length()
    and thus an ipv4 address will use approx, 32 bits
    '''
    @staticmethod
    def big_number_to_network_address(num, prefixlen):

        if int.from_bytes(
                num,
                'big'
        ).bit_length() == 128:

            return(network_object_v6(str.format(
                "{}/{}",
                network_object_v6(int.from_bytes(
                    num,
                    'big' )
                ).network_address,
                prefixlen ) ) )

        if int.from_bytes(
                num,
                'big'
        ).bit_length() == 32:

            return(network_object_v4(str.format(
                "{}/{}",
                network_object_v4(int.from_bytes(
                    num,
                    'big' )
                ).network_address,
                prefixlen ) ) )

    '''
    Gets the database a table object from this scope's database instance
    '''
    def get_db_table(self):
        return(self.db.table(str.format(
            "{}/{}",
            self.get_network_object(
            ).network_address,
            self.get_prefix() ) ) )

    '''
    Gets the TCP/IP version (4 or 6) of this scope
    '''
    def get_tcp_ip_ver(self):
        if not self.is_allocated():
            return(self.net_obj_ver)

        return(self.get_db_table().get(
            Query(
            ).scope != None
        ).get('tcp_ip_version') )

    '''
    Gets the current scope's parent scope or gets the current scopes "supernet"
    as defined by the IPv(x)Network class property supernet ( usually prefixlen - 1 )
    If allocated, parent scope object is created from DB, and returned
    '''
    def get_parent_scope(self):
        if self.parent_scope != None:
            return self.parent_scope

        elif self.is_allocated():
            if self.parent == None:
                parent = self.get_db_table(
                ).get(Query(
                ).scope != None
                ).get('parent')

                if parent != None:
                    self.parent_scope = self.get_new_scope_object(str.format(
                        "{}/{}",
                        parent.get('network'),
                        parent.get('prefix') ) )
                else:
                    self.l.warn('allocated scope is missing parent')

                    return(self.parent_scope)

        return(scope(
            tcp_ip_ver = self.get_tcp_ip_ver(),
            cidr = self.get_network_object(
            ).supernet() ) )

    '''
    Checks whether a specified list of tags match tags defined for this scope in the schema or whether
    any tags inhierited from propagated parent scope tags match, currently only supports one tag
    TODO return a dict of true/false values?
    '''
    def is_tagged(self, tags):
        self.l.debug(str.format(
            "current_scope: {} search for tag: {}",
            str(self),
            tags ) )

        parent_is_tagged = False

        if (self.parent_scope != None
            and self.inherit_tags_enabled() ):
            if self.parent_scope.is_tagged(tags):
                parent_is_tagged = True

        elif self.propagate_tags_enabled():
            if(len(list(filter(
                    lambda l: [ index for index in self.get_tags() if l == index ],
                    tags ) ) ) > 0 ):
                parent_is_tagged = True

        if not parent_is_tagged:
            return(len(list(filter(
                lambda l: [ index for index in self.get_tags() if l == index ],
                tags ) ) ) > 0 )

        else:
            return True

    '''
    Gets the tags defined for this scope
    '''
    def get_tags(self):
        if not self.is_allocated():
            self.l.debug(str.format(
                "current_scope: {} tags: {}",
                str(self),
                self.tags) )
            return(self.tags)

        answer = self.get_db_table(
        ).get(Query().scope != None
        ).get('tags')

        self.l.debug(str.format(
                "current_scope: {} tags: {}",
                str(self),
                answer) )

        return(answer)

    '''
    Constructor for scope class
    '''
    def __init__(
            self,
            cidr,
            db                = None,
            parent            = None,
            tcp_ip_ver        = 4,
            inherit_tags      = True,
            child_prefix      = None,
            preseed_children  = False,
            propagate_tags    = True,
            should_be_locked  = None,
            tags              = [] ):

        self.l                = logging.getLogger(__name__)
        self.propagate_tags   = propagate_tags
        self.child_prefix     = child_prefix
        self.net_obj_ver      = tcp_ip_ver
        self.cidr             = cidr
        self.prefix           = self.get_network_object().prefixlen
        self.parent_scope     = parent
        self.inherit_tags     = inherit_tags
        self.preseed_children = preseed_children
        self.tags             = tags
        self.should_be_locked = should_be_locked

        if db != None:
            self.own_db = False
            self.db = db

        else:
            self.own_db = True
            self.db = self.get_instance_db()

        self.l.debug(str.format(
            '''
            ( propagate_tags: {},
            child_prefix:     {},
            TCP/IP version:   {},
            CIDR:             {},
            prefixlen:        {},
            parent:           {},
            inherit_tags:     {},
            preseed_children: {} )|allocated={}
            ''',
            self.propagate_tags,
            self.child_prefix,
            self.net_obj_ver,
            self.cidr,
            self.prefix,
            str(self.parent_scope),
            self.inherit_tags,
            self.preseed_children,
            self.is_allocated() ) )

    '''
    Indicates whether this scope is using it's own DB file or not
    '''
    def use_own_db(self):
        return( self.own_db == True )

    '''
    Checks whether this scope should inherit tags propagated from the parent scope or not
    '''
    def inherit_tags_enabled(self):
        if not self.is_allocated():
            return(self.inherit_tags == True )

        return(self.get_db_table(
        ).get(
            Query(
            ).scope != None
        ).get('inherit_tags') == True )

    '''
    Checks whether all children for this scope should be enumerated and initialized by interpolation of
    the child prefixlen specified in the schema for this scope
    '''
    def preseed_children_enabled(self):
        if not self.is_allocated():
            return(self.preseed_children == True )

        return(self.get_db_table(
        ).get(
            Query(
            ).scope != None
        ).get('preseed_children') == True )

    '''
    Check whether if tags in this scope should be propagated to child scopes or not
    '''
    def propagate_tags_enabled(self):
        if not self.is_allocated():
            return(self.propagate_tags == True )

        return(self.get_db_table(
        ).get(
            Query().scope != None
        ).get('propagate_tags') == True )

    '''
    Gets the child prefixlen defined in the schema for this scope
    '''
    def get_child_prefix(self):
        if not self.is_allocated():
            return(self.child_prefix )

        return(self.get_db_table().get(
            Query(
            ).scope != None
        ).get('child_prefix') )

    '''
    gets a new allocatable scope object for a given network object
    '''
    def get_new_scope_object(self, net_obj):
        return(scope(
            cidr             = net_obj.compressed,
            propagate_tags   = self.propagate_tags_enabled(),
            inherit_tags     = self.inherit_tags_enabled(),
            preseed_children = self.preseed_children_enabled(),
            tags             = [],
            db               = ( self.use_own_db() == True
                                 and None
                                 or self.db ),
            parent           = self,
            tcp_ip_ver       = self.get_tcp_ip_ver() ) )

    '''
    Returns true if the network_address property of the parameter s
    equals either the get_network_object().network_address or
    get_network_object().broadcast_address of this scope and only
    if the child prefix of this scope or the child prefix specified as a parameter of this function is 32 or 128.
    '''
    def is_broadcast_or_scope_network_address(
            self,
            s,
            c_prefix       = None,
            mode           = None,
            operating_mode = None ):

        self.l.debug(str.format(
            '''
            mode:                   {}
            operating_mode:         {}
            s_network_address:      {}
            self_network_address:   {}
            self_broadcast_address: {}
            ''',
            mode,
            operating_mode,
            str(s.network_address),
            str(self.get_network_object(
            ).network_address ),
            str(self.get_network_object(
            ).broadcast_address ) ) )

        return( ( str(s.network_address)
                  == str(self.get_network_object(
                  ).network_address )
                  or str(s.network_address)
                  == str(self.get_network_object(
                  ).broadcast_address ) )
                and ( ( c_prefix
                        and ( c_prefix
                              == 32
                              or c_prefix
                              == 128 )
                        == True)
                      or ( self.get_child_prefix()
                           == 32
                           or self.get_child_prefix()
                           == 128 ) ) )

    '''
    modes:
    0x2: pre-seed mode
    0x4: enumerate a single allocated and un-owned or unallocated scope from the current scope
    0x8: enumerate owned scopes from the current scope until an unallocated scope is reached
    0x8|0x2: enumerate sparsely allocated owned scopes throughout the current scope
    '''
    def children(
            self,
            child_net_obj = None,
            mode = 0x2 ):

        operating_mode = mode

        c_prefix = ( child_net_obj != None
                     and child_net_obj.prefixlen
                     or self.get_child_prefix() )

        if mode == 0x4 and self.is_locked():
            raise(Exception(str.format(
                "current scope is locked, interpolation cannot continue in mode {}", mode) ) )

        for index in self.get_network_object(
        ).subnets(
            new_prefix = c_prefix ) :

            s = None

            if operating_mode == 0x0:
                break

            if operating_mode == 0x2:
                s = self.get_new_scope_object(index)

                if self.preseed_children_enabled():
                    yield(s)

            if operating_mode == 0x4:
                if self.is_broadcast_or_scope_network_address(
                        index,
                        c_prefix,
                        mode,
                        operating_mode ):

                    continue

                s = self.get_new_scope_object(index)
                if s.is_allocated() and not s.is_owned():
                    operating_mode = operating_mode ^ 0x4

                    yield(s)

                elif not s.is_allocated():
                    operating_mode = operating_mode ^ 0x4

                    yield(s)

            if operating_mode & 0x8:
                if self.is_broadcast_or_scope_network_address(
                        index,
                        c_prefix,
                        mode,
                        operating_mode ):

                    continue

                s = self.get_new_scope_object(index)

                if s.is_allocated() and s.is_owned():
                    yield(s)

                elif not s.is_allocated() and not ( operating_mode & 0x2 ):
                        operating_mode = operating_mode ^ 0x8

    '''
    Gets the prefixlen of the current scope
    '''
    def get_prefix(self):
        return(self.prefix) # don't muck up the DB by trying to retrieve this
                            # value from the DB just rely on the class prop
                            # too many circular dependencies

    '''
    Gets a unique id for the current scope
    '''
    def get_scope_id(self):
        return(str.format(
            "{}/{}",
            self.network_address_to_big_number(),
            self.get_prefix() ) )

    '''
    Gets either an IPv6Network or IPv4Network object, classes come from
    the python ipaddress module
    '''
    def get_network_object(self, cidr=None):
        if self.net_obj_ver == 4:
            return( network_object_v4( (
                cidr != None
                and cidr
                or self.cidr ) ) )

        elif self.net_obj_ver == 6:
            return( network_object_v6( (
                cidr != None
                and cidr
                or self.cidr ) ) )

        else:
            raise Exception("invalid TCP/IP version or unsupported")

    '''
    Checks whether or not the current scope has a database table entry
    '''
    def is_allocated(self):
        return((self.get_db_table(
        ).get(Query(
        ).scope
              != None ) )
               != None )

    '''
    Adds tags to the current scope
    '''
    def add_tags(self, tags):
        self.l.debug(str.format("for scope: {} adding tags: {}", self.get_network_object(), tags ) )

        if self.is_locked():
            raise Exception("scope is locked, can't set tags")

        cur = self.get_db_table(
        ).get( (
            Query().scope != None )
        ).get('tags')

        self.get_db_table().update( { 'tags': cur + tags } )

        self.update_scope_change_log({
            'reason': "tags were added",
            'tags': tags } )

        return(self)

    '''
    Deletes tags from the current scope
    '''
    def delete_tags(self, tags):
        self.l.debug(str.format("for scope: {} delete tags: {}", self.get_network_object(), tags ) )

        if self.is_locked():
            raise Exception("can't delete tags, locked")

        new_tags = list(filter(
            lambda x: [y for y in self.get_db_table(
            ).get((
                Query().scope != None )
            ).get('tags') if x != y], tags
        ) )

        self.get_db_table().update( { 'tags': new_tags } )

        self.update_scope_change_log({
            'reason': 'tags were removed',
            'removed_tags': tags,
            'new_tags': new_tags
        } )

        return(self)

    '''
    Unlocks the current scope indicating that no operations such as interpolation may be performed,
    with the exception of pre-seeded scopes.
    '''
    def unlock_scope(self):
        self.l.debug(str.format(
            "unlocking scope: {}",
            self.get_network_object() ) )

        if not self.is_locked():
            raise Exception(str.format(
                "{} scope is already unlocked",
                self.get_network_object().compressed ) )

        self.get_db_table().update( { 'locked': False } )

        self.update_scope_change_log( { 'reason': "scope was unlocked" } )

        return(self)

    '''
    Sets the current scopes locked setting indicating that no changes may be made nor child scopes created, with
    exception to pre-seeding
    '''
    def lock_scope(self):
        self.l.debug(str.format(
            "locking scope: {}",
            self.get_network_object() ) )

        if self.is_locked():
            raise Exception("scope is already locked")

        self.get_db_table().update( { 'locked': True } )

        self.update_scope_change_log( {'reason': "scope was locked" } )

        return(self)

    '''
    Indicates whether or not the current scope is assigned
    '''
    def is_owned(self):
        if not self.is_allocated():
            raise Exception("scope is not allocated, and therefore is not and cannot be owned")

        return(
            self.get_db_table(
            ).get( (
                Query().scope != None )
            ).get('owner') != None )

    '''
    Indicates whether or not the current scope is locked
    '''
    def is_locked(self):
        if not self.is_allocated():
            raise Exception("scope is not allocated, can't be locked")

        return(
            self.get_db_table(
            ).get( (
                Query().scope != None )
            ).get('locked') == True )

    '''
    '''
    def scope_should_be_locked(self):
        if not self.is_allocated():
            return(self.should_be_locked)

        elif self.is_allocated():
              self.lock_down = self.get_db_table(
              ).get((Query(
              ).scope != None )
              ).get('should_be_locked')

              if self.lock_down:
                  return(self.lock_down)

              elif self.get_parent_scope() != None:
                  return(self.get_parent_scope(
                  ).should_be_locked() == True )

    '''
    Updates the changelog for the current scope
    '''
    def update_scope_change_log(self, reason):
        self.l.debug(str.format(
            "updating scope: {} changelog reason: {}",
            self.get_network_object(),
            reason ) )

        if not self.is_allocated():
            raise Exception("scope is not yet allocated")

        cur_change_log = (self.get_db_table(
        ).get((
            Query().scope != None )
        ).get('change_log') )

        cur_change_log.append({
            "modification_date": str(datetime.datetime.now() ),
            "reason": reason
        } )

        self.get_db_table().update( { 'change_log': cur_change_log } )

        return(self)

    '''
    Creates a database table and saves the current scope
    '''
    def initialize_allocation(self):
        self.l.debug(str.format(
            "initializing scope allocation: {}",
            self.get_network_object() ) )

        if self.is_allocated():
            raise Exception("already allocated")

        self.get_db_table().insert({
            'scope': {
                'network':      self.network_address_to_big_number(),
                'prefix':       self.get_prefix()
            },
            'created':          str( datetime.datetime.now() ),
            'owner':            None,
            'locked':           False,
            'should_be_locked': self.scope_should_be_locked(),
            'preseed_children': self.preseed_children_enabled(),
            'propagate_tags':   self.propagate_tags_enabled(),
            'inherit_tags':     self.inherit_tags_enabled(),
            'child_prefix':     self.get_child_prefix(),
            'tcp_ip_version':   self.get_tcp_ip_ver(),
            'change_log':       [],
            'tags':             self.get_tags(),
            'parent_scope': {
                'network':      self.get_parent_scope().network_address_to_big_number(),
                'prefix':       self.get_parent_scope().get_prefix() } } )

        return(self)

    '''
    Sets the owner for the current scope (ownership indicates assignment)
    '''
    def set_owner(self, new_owner):
        self.l.debug(str.format(
            "setting scope: {} owner {}",
            self.get_network_object(),
            new_owner ) )

        if self.is_locked():
            raise Exception("locked can't set owner")

        if self.is_owned():
            raise Exception("already owned, must use clear_ownership() owner first")

        self.get_db_table().update( { 'owner': new_owner } )

        self.update_scope_change_log({
            'reason': "new owner was assigned",
            'owner': new_owner
        } )

        return(self)

    '''
    Gets an allocated child scope from the current scope that is not currently assigned
    '''
    def get_unassigned_scope(self):

        self.l.debug(str.format(
            "requested unassigned child scope for current scope: {}",
            self.get_network_object() ) )

        for index in self.children(
                mode = 0x4 ):
            if index.is_allocated() and not index.is_owned():
                self.l.debug(str.format(
                    "found previously allocated unassigned child scope {}",
                    index ) )

                return(index)

            elif not index.is_allocated():
                self.l.debug(str.format(
                    "found un-allocated (never before owned) child scope {}",
                    index ) )

                return(index)

        raise Exception('no unassigned scopes available')

    '''
    Erases the current scopes ownership (making it re-assignable)
    '''
    def clear_ownership(self):
        self.l.debug(str.format(
            "clearing ownership for scope: {}",
            self.get_network_object() ) )

        if self.is_locked():
            raise Exception("can't erase ownership, locked")

        if not self.is_owned():
            raise Exception("clear ownership called but scope is not owned")

        self.get_db_table().update( { 'owner': None } )

        self.update_scope_change_log( { 'reason': "ownership was cleared" } )

        return(self)

    '''
    Deletes the current scope allocation and database if using it's own DB file, otherwise
    just deletes it's table
    '''
    def delete_scope(self):
        self.l.debug(str.format(
            "deleting scope: {}",
            self.get_network_object() ) )

        if self.is_allocated() and self.is_locked():
            raise Exception("scope is locked, can't delete until unlocked")

        self.db.drop_table(str.format(
            "{}/{}",
            self.get_network_object().network_address,
            self.get_prefix() ) )

        if self.use_own_db() == True:
            self.db.close()

            os.remove(str.format(
                "/data/{}.{}.json",
                self.network_address_to_big_number(),
                self.get_prefix()
            ) )

        return(self)

    '''
    Retrieves a scope of prefixlen 32 (for IPv4) or 128 (for IPv6) - A single address
    in either case
    '''
    def lease_network_address(self):
        self.l.debug(str.format(
            'leasing IP address from scope: {}',
            self.get_network_object().network_address ) )

        for index in self.children(
                child_net_obj = (
                    self.get_tcp_ip_ver() == 4
                    and self.get_network_object("0.0.0.0/32")
                    or  self.get_network_object("0::/0") ),
                mode = 0x4 ):

            return(index)

        raise Exception("no un-leased addresses available in scope")

    '''
    Retrieves an existing /32 or /128 (single address) scope
    '''
    def get_network_address(self, address):
        self.l.debug(str.format(
            'for current scope {} looking for existing child scope allocation {}',
            self.get_network_object().compressed,
            address ) )

        request = None

        if type(address) == str:
            request = self.get_network_object(address)

        elif type(address) == type(self.get_network_object()):
            request = address

        else:
            raise Exception('unknown type for address parameter')

        for index in self.children(
                child_net_obj = (
                    self.get_tcp_ip_ver() == 4
                    and self.get_network_object("0.0.0.0/32")
                    or  self.get_network_object("0::/128") ),
                mode = 0x8 ):

            if index.get_network_object() == request:
                return(index)

        raise Exception("Requested scope was not found")
