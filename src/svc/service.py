import json, logging, traceback, sys, datetime, itertools
from .scope import scope
from .scope_factory import scope_factory
from ipaddress import IPv6Network as n6, IPv4Network as n4

"""
"""
class service():
    '''
    '''
    def __init__(self):
        self.l = logging.getLogger(__name__)

        self.h = [
             ( "Content-Type", "application/vnd.docker.plugins.v1.2+json" ) ]

        self.f = scope_factory()
        self.f.initialize()

    '''
    Retrieves default HTTP response headers list of tuples (header/value pairs)
    '''
    def get_standard_headers(self):
        self.l.debug((
            request,
            request.data ) )

        return(self.h)

    '''
    Docker plugin activate service call
    '''
    def activate(self, request):
        self.l.debug((
            request,
            request.data ) )

        try:
            response = (
                200,
                json.dumps({
                    "Implements": ["IpamDriver"] } ),
                self.h )

        except Exception as ex:
            self.l.error(ex, exc_info = True)

            response = (
                500,
                json.dumps({
                    "Err": (
                        hasattr('ex', 'message')
                        and ex.message
                        or "see error log for details" ) } ),
                self.h )

        finally:
            return(response)


    '''
    Gets service capabilities for plugin
    '''
    def get_capabilities(self, request):
        self.l.debug((
            request,
            request.data ) )

        try:
            response = (
                200,
                json.dumps({
                    "RequiresMACAddress": "true" } ),
                self.h )

        except Exception as ex:
            self.l.error(ex, exc_info = True)

            response = (
                500,
                json.dumps({
                    "Err": (
                        hasattr('ex', 'message')
                        and ex.message
                        or "see error log for details" ) } ),
                self.h )

        finally:
            return(response)

    '''
    '''
    def get_default_address_spaces(self, request):
        self.l.debug((
            request,
            request.data ) )

        try:
            response = (
                200,
                json.dumps({
                    "LocalDefaultAddressSpace": "default",
                    "GlobalDefaultAddressSpace": "default" } ),
                self.h )

        except Exception as ex:
            self.l.error(ex, exc_info = True)

            response = (
                500,
                json.dumps({
                    "Err": (
                        hasattr('ex', 'message')
                        and ex.message
                        or "see error log for details" ) } ),
                self.h )

        finally:
            return(response)

    '''
    '''
    def request_pool(self, request):
        self.l.debug((
            request,
            request.data ) )

        parent    = None
        child     = None
        response  = None
        candidate = None

        try:
            data = json.loads(request.data)

            docker_requested_pool = data.get('Pool')

            docker_requested_sub_pool = data.get('SubPool')

            id = data.get(
                    'Options'
                ).get('id')

            id = (id != None
                  and id
                  or "not specified" )

            scope_filter_tags = ( data.get(
                'Options'
            ).get(
                'scope_filter_tags'
            ) != None
                     and data.get(
                         'Options'
                     ).get(
                         'scope_filter_tags'
                     ).split(
                         ',')
                     or ['_default_'] )

            parent, child = self.f.get_allocated_network_scope(
                filter_tags              = scope_filter_tags,
                net_obj_or_id_and_prefix = (
                    docker_requested_sub_pool != None
                    and docker_requested_sub_pool
                    or None ),
                parent_net_or_net_obj    = (
                    docker_requested_pool != None
                    and docker_requested_pool
                    or None ) )

            candidate = ( child
             or parent
            ).unlock_scope(
            ).get_unassigned_scope()

            ( candidate.is_allocated()
              and candidate.unlock_scope(
             ).set_owner(
                 id
             ).lock_scope()
              or candidate.initialize_allocation(
             ).set_owner(
                 id
             ).lock_scope() )

            response = (
                200,
                json.dumps({
                    "PoolID": candidate.get_scope_id() ,
                    "Pool": candidate.get_network_object().compressed,
                    "Data": { } } ),
                self.h )

            return(response)

        except Exception as ex:
            self.l.error(ex, exc_info = True)

            response = (
                500,
                json.dumps({
                    "Err": (
                        hasattr('ex', 'message')
                        and ex.message
                        or "see error log for details" ) } ),
                self.h )

        finally:
            ( child != None
             and ( not child.is_locked()
                   and child.lock_scope() ) )

            ( parent != None
             and ( not parent.is_locked()
                   and parent.lock_scope() ) )

            ( candidate != None
              and ( not candidate.is_locked()
                    and candidate.lock_scope() ) )

            return(response)

    '''
    '''
    def release_pool(self, request):
        self.l.debug((
            request,
            request.data ) )

        parent   = None
        child    = None
        response = None

        try:
            data = json.loads(request.data)

            pool_net = data.get('PoolID')

            parent, child = self.f.get_allocated_network_scope(
                net_obj_or_id_and_prefix = pool_net )

            ( child
              or parent
            ).unlock_scope(
            ).clear_ownership(
            ).lock_scope()

            response = (
                200,
                json.dumps( { } ),
                self.h )

        except Exception as ex:
            self.l.error(ex, exc_info = True)

            response = (
                500,
                json.dumps({
                "Err": (
                    hasattr('ex', 'message')
                    and ex.message
                    or "see error log for details" ) } ),
                self.h )

        finally:
            ( child != None
             and ( not child.is_locked()
                   and child.lock_scope() ) )

            ( parent != None
             and ( not parent.is_locked()
                   and parent.lock_scope() ) )

            return(response)

    '''
    '''
    def request_address(self, request):
        self.l.debug((
            request,
            request.data ) )

        network_addr = None
        parent       = None
        child        = None
        response     = None

        try:
            data = json.loads(request.data)

            pool_net = data.get('PoolID')

            options = data.get('Options')

            owner = (
                options != None
                and ( options.get(
                    'RequestAddressType' ) != None
                     and options.get(
                         'RequestAddressType' )
                     or 'not specified' )
            or 'not specified' )

            parent, child = self.f.get_allocated_network_scope(
                parent_net_or_net_obj = pool_net )

            network_addr = ( child
                            or parent
            ).unlock_scope(
            ).lease_network_address()

            ( child
            or parent
            ).lock_scope()

            network_addr = (
                not network_addr.is_allocated()
                and network_addr.initialize_allocation()
                or network_addr.unlock_scope()
            ).set_owner(
                owner
            ).lock_scope()

            response = (
                200,
                json.dumps({
                    "Address": str.format(
                        "{}/{}",
                        network_addr.get_network_object().network_address,
                        network_addr.parent_scope.get_prefix() ),
                    "Data": {} } ),
                self.h )

        except Exception as ex:
            self.l.error(
                ex,
                exc_info = True )

            response = (
                500,
                json.dumps({
                    "Err": (
                        hasattr('ex', 'message')
                        and ex.message
                        or "see error log for details" ) } ),
                self.h )

        finally:
            ( child != None
             and ( not child.is_locked()
                   and child.lock_scope() ) )

            ( parent != None
             and ( not parent.is_locked()
                   and parent.lock_scope() ) )

            ( network_addr != None
              and ( not network_addr.is_locked()
                    and network_addr.lock_scope() ) )

            return(response)

    '''
    '''
    def release_address(self, request):
        self.l.debug((
            request,
            request.data ) )

        parent    = None
        child     = None
        response  = None
        candidate = None

        try:
            data = json.loads(request.data)

            pool_net  = data.get('PoolID')

            options = data.get('Options')

            address = str.format(
                "{}/32",
                data.get('Address') )

            parent, child = self.f.get_allocated_network_scope(
                parent_net_or_net_obj       = pool_net )

            candidate = ( child
                          or parent
            ).get_network_address(address)

            ( cadidate.is_owned()
             and candidate.unlock_scope(
             ).clear_ownership(
             ).lock_scope() )

            response = (
                200,
                json.dumps({ }),
                self.h )

        except Exception as ex:
            self.l.error(
                ex,
                exc_info = True )

            response = (
                500,
                json.dumps({
                    "Err": (
                        hasattr('ex', 'message')
                        and ex.message
                        or "see error log for details" ) } ),
                self.h )

        finally:
            ( child != None
             and ( not child.is_locked()
                   and child.lock_scope() ) )

            ( parent != None
             and ( not parent.is_locked()
                   and parent.lock_scope() ) )

            ( candidate != None
              and ( not candidate.is_locked()
                    and candidate.lock_scope() ) )

            return(response)
