import json, logging, itertools
from .scope import scope
from ipaddress import IPv6Network as n6, IPv4Network as n4

'''
Simple usage:

from svc.scope_factory import scope_factory as sf

f = sf()

s = f.initialize()

'''
class scope_factory():
    '''
    Creates a new instance of the scope factory

    Parameters:

    schema (str): A path to the scope schema JSON file, defaults to /work/schema.json
    db (TinyDB): A tinyDB instance. If specified, is passed by reference to each scope object instance.

    '''
    def __init__(
            self,
            schema   = '/work/schema.json',
            db       = None ):

        self.schema  = json.load(open(schema ) )
        self.db      = db
        self.l       = logging.getLogger(__name__)
        self.scopes  = []

        if self.db != None:
            self.use_own_db = False
        else:
            self.use_own_db = True

        self.l.debug((str.format(
            "schema: <{}...>, db: {}",
            str(self.schema)[:50],
            self.db ) ) )

    '''
    '''
    @staticmethod
    def get_ip_ver_4_network_object(net):
        return(n4(net))

    '''
    '''
    @staticmethod
    def get_ip_ver_6_network_object(net):
        return(n6(net))

    '''
    Retrieves the top level network object from the schema for the specified tcp/ip
    version (4 or 6.)
    '''
    def get_top_level_network_object(self, tcp_ip_ver):
        candidate = None

        try:
            candidate = next(filter(
                lambda s:
                s.get_tcp_ip_ver() == tcp_ip_ver
                and s.parent_scope == None,
                self.scopes ) ).get_network_object()

        except StopIteration as ex:
            self.l.info(str.format(
                "none available, using {}",
                ( tcp_ip_ver == 4
                 and n4('0.0.0.0/0')
                 or n6('0::/0') ) ) )

            candidate = ( tcp_ip_ver == 4
                 and n4('0.0.0.0/0')
                      or n6('0::/0') )
        finally:
            return(candidate)



    '''
    Converts encoded id (ex: 3323088896/30) to a network object
    '''
    def network_id_to_network_object(
            self,
            ulong_or_ulonglong_cidr_net,
            prefixlen ):

        return( scope.big_number_to_network_address(
            int( ulong_or_ulonglong_cidr_net ).to_bytes(
                16,
                'big' ),
            int( prefixlen ) ) )

    '''
    Retrieve a single known and allocated or unknown but allocated scope
    '''
    def get_allocated_network_scope(
            self,
            net_obj_or_id_and_prefix = None,
            parent_net_or_net_obj    = None,
            filter_tags              = [] ):

        request_net    = None
        parent_net     = None
        to_filter      = filter_tags
        p_s_enumerator = None

        if net_obj_or_id_and_prefix and type(net_obj_or_id_and_prefix) == str:
            id, prefix = net_obj_or_id_and_prefix.split('/')

            request_net = self.network_id_to_network_object(
                id,
                int( prefix ) )

        elif net_obj_or_id_and_prefix and type(net_obj_or_id_and_prefix) == tuple:
            request_net = self.network_id_to_network_object(
                net_obj_or_id_and_prefix[ 0 ],
                int( net_obj_or_id_and_prefix[ 1 ] ) )

        if parent_net_or_net_obj != None:
            if type(parent_net_or_net_obj) == str:
                id, prefix = parent_net_or_net_obj.split('/')

                parent_net = self.network_id_to_network_object(
                id,
                int( prefix ) )

            elif type(parent_net_or_net_obj) == tuple:
                parent_net = self.network_id_to_network_object(
                    parent_net_or_net_obj[ 0 ],
                    int( parent_net_or_net_obj[ 1 ] ) )

            p_s_enumerator = lambda factory: sorted(
                [ index for index in factory.scopes
                  if type(index.get_network_object() )
                  == type(parent_net) ],
                key = lambda s: s.parent_scope != None,
                reverse = True )

        else:
            if request_net == None:
                p_s_enumerator = lambda factory: sorted(
                    [ index for index in factory.scopes
                      if type(index.get_network_object() )
                      == type(parent_net) ],
                    key = lambda s: s.parent_scope != None,
                    reverse = True )

                parent_net = self.get_top_level_network_object(4)

                if( filter_tags == None or len(filter_tags) == 0 ):
                    to_filter = ['default']

            else:
                p_s_enumerator = lambda factory: sorted(
                    [ index for index in factory.scopes
                      if type(index.get_network_object() )
                      == type(request_net) ],
                    key = lambda s: s.parent_scope != None,
                    reverse = True )


        self.l.debug(str.format(
            '''
            request_net: {}
            parent_net:  {}
            ''',
            request_net,
            parent_net ) )

        for parent, child in self.get_target_scopes(
                net_obj        = request_net,
                parent_net_obj = parent_net,
                p_s_enumerator = p_s_enumerator,
                c_s_enumerator = lambda e, m: e.children( mode = 0x8 ),
                filter_tags    = to_filter ):

            self.l.debug(str.format(
                '''
                parent_scope: {}
                child_scope:  {}
                ''',
                parent,
                child ) )

            return( ( parent, child ) )
    '''
    Expands a given parent scope using the schema-defined child prefixlen value for interpolation
    '''
    def get_child_scopes(
            self,
            net,
            parent_scope,
            filter_tags  = None,
            c_e_mode     = 0x8,
            s_enumerator = lambda e, m: e.children( mode = m ),
            c_s_filter   = lambda factory, s, n, t: factory.child_scope_filter( s, n, t ) ):

        for index in s_enumerator(parent_scope, c_e_mode):
            self.l.debug(str.format("{}", index ) )

            if c_s_filter(self, index, net, filter_tags):
                yield(index)

    '''
    Enumerates a working set of scopes from the parent (schema defined) and child (parent expanded) scopes
    given a CIDR/prefixlen and/or parent scope to enumerate from or a list of tags with which to select
    scopes.
    '''
    def get_target_scopes(
            self,
            net_obj        = None,
            parent_net_obj = None,
            filter_tags    = [],
            c_s_enumerator = None,
            p_s_enumerator = None,
            c_s_filter     = None,
            p_s_filter     = None ):

        if ( parent_net_obj
             == None
             and net_obj
             == None
             and ( filter_tags
                   == None
             or len(filter_tags)
                   == 0 ) ):

            raise Exception("need net_obj to locate parent_net_obj or filter tags to start with", filter_tags)

        for parent_scope in self.get_parent_scopes(
                net              = ( parent_net_obj != None
                                   and parent_net_obj
                                   or net_obj ),
                filter_tags      = ( parent_net_obj == None
                                     and ( len( filter_tags ) != 0
                                           and filter_tags
                                           or ( net_obj == None
                                                and ( _ for _ in () ).throw(Exception(
                                                    "filter tags required when no parent scope is specified")
                                                or filter_tags ) ) )
                                     or filter_tags ),
                s_enumerator     = ( p_s_enumerator != None
                                   and p_s_enumerator
                                   or ( lambda factory: factory.scopes ) ),
                p_s_filter       = lambda factory, s, n, t: factory.parent_scope_filter( s, n, t ) ):

            self.l.debug(parent_scope)

            for child_scope in self.get_child_scopes(
                    net          = net_obj,
                    parent_scope = parent_scope,
                    filter_tags  = filter_tags,
                    c_e_mode     = ( parent_net_obj != None
                                     and 0x4
                                     or 0x8 ),
                    c_s_filter   = lambda factory, s, n, t: factory.child_scope_filter( s, n, t ),
                    s_enumerator = ( c_s_enumerator != None
                                     and c_s_enumerator
                                     or ( lambda e, m: e.children( mode = m ) ) ) ):

                self.l.debug(str.format(
                    'enumerated parent: {} and child: {}',
                    parent_scope,
                    child_scope ) )

                yield( ( parent_scope, child_scope ) )

            self.l.debug(str.format(
                'enumerated parent: {}',
                parent_scope ) )

            yield( ( parent_scope, None ) )

    '''
    '''
    def child_scope_filter(self, s, n, t):
        self.l.debug('filter not implemented, children unfiltered')

        return(True)

    '''
    default filter conditions, asides from filter tags, with which to select scopes from the parent scopes
    category
    '''
    def parent_scope_filter(self, s, n, t):
        self.l.debug(str.format(
            '''
            scope:     {}
            net_obj:   {}
            tags:      {}
            ''',
            str(s),
            n,
            t ) )

        ret = True

        if ( n != self.get_top_level_network_object(
                 type(n) == n4
                 and 4
                 or 6 ) ):

            if not n.subnet_of(s.get_network_object() ):
                self.l.debug(str.format(
                    'filtered {} is not subnet of {}',
                    n,
                    s.get_network_object() ) )

                ret = False

        if type(t) == list and len(t) > 0:
            if not s.is_tagged(t):
                self.l.debug(str.format(
                    'filtered {} is not tagged {}',
                    str(s),
                    t ) )

                ret = False

        return(ret)

    '''
    Enumerates parent scopes defined in the schema as scope objects
    '''
    def get_parent_scopes(
            self,
            net,
            filter_tags  = [],
            p_s_filter   = lambda factory, s, n, t: factory.parent_scope_filter( s, n, t ),
            s_enumerator = lambda factory: factory.scopes ):

        for index in s_enumerator(self):
            self.l.debug('hi')
            if p_s_filter(
                    self,
                    index,
                    net,
                    filter_tags ):

                yield(index)

    '''
    Parses schema and creates/initializes top-level existing scopes, method is recursive

    Parameters:
    current (dict): First call should be none, used during recursion to process nested scope blocks defined in the schema
    parent (scope): the current (to-be) scope's parent scope
    parent_schema (dict): the parent schema of the current (to-be) scope

    Returns:
    scope_factory: this instance (self)

    '''
    def initialize(
            self,
            current       = None,
            parent        = None,
            parent_schema = None ):

        self.l.debug(str.format(
            '''
            args: current_schema: <{}...>
            parent:               {}
            parent_schema:        <{}...>
            ''',
            str( current )[ :50 ],
            parent,
            str( parent_schema )[ :50 ] ) )

        if current == None:
            [ self.initialize( current = index )
              for index in self.schema.get('scopes') ]

            return(self.scopes)

        else:
            s = scope(
                cidr = str.format(
                    '{}/{}',
                    current.get('network'), (
                        current.get('prefix') != None
                        and current.get('prefix')
                        or ( parent != None
                             and parent.get_child_prefix()
                             or ( _ for _ in () ).throw(Exception(
                                 'missing required schema parameter for child prefix' ) ) ) ) ),
                child_prefix = current.get('child_prefix'),
                parent = parent,
                tags = (
                    current.get('tags') != None
                    and current.get('tags')
                    or [] ),
                preseed_children = (
                    parent != None
                    and parent.preseed_children_enabled()
                    or ( current.get('pre_seed_children')
                         and current.get('pre_seed_children')
                         or False ) ),
                propagate_tags = (
                    current.get('propagate_tags') != None
                    and current.get('propagate_tags')
                    or False ),
                tcp_ip_ver = (
                    current.get('tcp_ip_version') != None
                    and current.get('tcp_ip_version')
                    or ( parent != None
                         and parent.get_tcp_ip_ver()
                         or (_ for _ in ()).throw(Exception(
                             'missing required schema parameter for TCP/IP version') ) ) ),
                db = (
                    self.use_own_db
                    and self.db
                    or None ),
                should_be_locked = (
                    current.get('lock_down')
                    and current.get('lock_down')
                    or None ),
                inherit_tags = (
                    current.get('inherit_tags')
                    and current.get('inherit_tags')
                    or ( parent != None
                        and parent.propagate_tags_enabled()
                        or True ) ) )

            if ( not s.is_allocated() ):
                s.initialize_allocation()

                self.scopes.append(s)

                [ self.initialize(
                    current       = index,
                    parent        = s,
                    parent_schema = current )
                  for index in current.get('scopes') ]

                if s.preseed_children_enabled():
                    [ self.scopes.append( ( ( not index.is_allocated()
                          and (
                              current.get('lock_down') )
                          or (
                              parent_schema != None
                              and parent_schema.get('lock_down') ) )
                         and (
                             index.initialize_allocation().lock_scope() ) )
                        or (
                            index.is_allocated()
                            and index ) )
                        for index in s.children(
                                mode = 0x2 ) ]

                if ( current.get('lock_down')
                    or (
                        parent_schema != None
                        and parent_schema.get('lock_down') ) ):
                    s.lock_scope()

                return

            elif s.is_allocated():
                if current.get('lock_down') == True and not s.is_locked():
                    self.l.warn(str.format(
                        "schema says scope {} should be locked down but it isn't current_schema: <{}...>",
                        s.get_network_object(),
                        str( current )[ :50 ] ) )

                self.scopes.append(s)

                if s.preseed_children_enabled():
                    [ self.scopes.append(index) for index in s.children(
                        mode = 0x2 ) ]

                [ self.initialize(
                    current       = index,
                    parent        = s,
                    parent_schema = current )
                  for index in current.get('scopes') ]

                return
