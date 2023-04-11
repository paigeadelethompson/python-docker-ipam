import sys, logging, json
from flask import Flask, request as r, Response as R
from src.svc.service import service

def setup_logging():
    formatter = logging.Formatter(
        fmt = "%(levelname)s|%(module)s->%(funcName)s %(message)s" )

    handler = logging.StreamHandler(
        sys.stdout )

    handler.setFormatter(
        formatter )

    logger = logging.getLogger()

    logger.setLevel(
        logging.DEBUG )

    logger.addHandler(
        handler )

    return logger

l = setup_logging()
f = Flask(__name__)
s = service()

f.errorhandler(Exception)
def handle_invalid_usage(error):
    resp = json.dumps({
        "Err": str.format(
            "a critical error has occurred {}",
            error ) } )

    return(R(
        status   = 500,
        response = resp,
        headers  = dict(s.get_standard_headers() ) ) )

@f.errorhandler(NotImplementedError)
def handle_invalid_usage(error):
    resp = json.dumps({
        "Err": str.format(
            "request not implemented {}",
            error ) } )

    return(R(
        status   = 501,
        response = resp,
        headers  = dict(s.get_standard_headers() ) ) )

@f.route(
    '/Plugin.Activate',
    methods = ['POST'] )
def Activate():
    status, resp, headers = s.activate(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )


@f.route(
    '/IpamDriver.GetCapabilities',
    methods = ['POST'] )
def GetCapabilities():
    status, resp, headers = s.get_capabilities(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )

@f.route(
    '/IpamDriver.GetDefaultAddressSpaces',
    methods = ['POST'] )
def GetDefaultAddressSpaces():
    status, resp, headers = s.get_default_address_spaces(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )

@f.route(
    '/IpamDriver.RequestPool',
    methods = ['POST'] )
def RequestPool():
    status, resp, headers = s.request_pool(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )

@f.route(
    '/IpamDriver.ReleasePool',
    methods = ['POST'] )
def ReleasePool():
    status, resp, headers = s.release_pool(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )

@f.route(
    '/IpamDriver.RequestAddress',
    methods = ['POST'] )
def RequestAddress():
    status, resp, headers = s.request_address(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )

@f.route(
    '/IpamDriver.ReleaseAddress',
    methods = ['POST'] )
def ReleaseAddress():
    status, resp, headers = s.release_address(r)

    return(R(
        status   = status,
        response = resp,
        headers  = dict(headers) ) )

if __name__ == '__main__':
    raise Exception(str.format(
        "Are you starting this web server with uWSGI?") )
else:
    l.debug(str.format("uwsgi ready to serve requests") )
