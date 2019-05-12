#!/usr/bin/env python3
import io
import sys
import gzip
import json
import click
import traceback
import logging


import falcon
from falcon_cors import CORS
from wsgiref import simple_server


logger = logging.getLogger(__name__)


supported_methods = ['GET', 'POST', 'PUT', 'DELETE']
class GzipMiddleware:
    def process_request(self, req, resp):
        #print(req.headers)
        if 'CONTENT-ENCODING' in req.headers and 'gzip' == req.headers['CONTENT-ENCODING']:
            logger.info('using gzip middleware to decompress')
            req.stream = gzip.GzipFile(fileobj=req.stream)
    def process_response(self, req, resp, resource, req_succeeded):
        if req.method not in supported_methods:
            return

        if 'ACCEPT-ENCODING' in req.headers and 'gzip' in req.headers['ACCEPT-ENCODING']:
            logger.info('using gzip middleware to compress')
            if type(resp.body) == str:
                resp.body = resp.body.encode('utf8')
            resp.body = gzip.compress(resp.body)
            resp.set_header('CONTENT-ENCODING', 'gzip')
        pass


class ResourceBasedMiddleware:
    def process_resource(self, req, resp, resource, params):
        if req.method not in supported_methods:
            raise falcon.HTTPInternalServerError()

        try:
            req.data = None
            if type(resource) == DATAResources:
                if req.method in ['GET', 'DELETE']:
                    req.data = {}
                if req.method in ['POST', 'PUT', 'DELETE']:
                    try:
                        req.data = req.stream.read()
                        req.data = json.loads(req.data.decode('utf8'))
                    except:
                        req.data = {}
            if type(resource) == RAWResources:
                req.data = req.stream.read()
            if req.data == None:
                raise Exception(f'request {req} cannot be processed for resource {resource}')
        except:
            logger.warn('Failed to preprocess:')
            logger.warn(req)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = ''.join(traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback))
            logger.warn(stacktrace)
            raise falcon.HTTPInternalServerError()

    def process_response(self, req, resp, resource, req_succeeded):
        if req.method not in supported_methods:
            raise falcon.HTTPInternalServerError()

        if resp.data == None:
            raise falcon.HTTPInternalServerError()

        if type(resource) == DATAResources:
            resp.body = json.JSONEncoder().encode(resp.data).encode('utf8')
            resp.content_length = len(resp.body)
            resp.content_type = 'application/json'

        if type(resource) == RAWResources:
            if not resp.data:
                raise falcon.HTTPInternalServerError()
            resp.body = resp.data
            resp.content_length = len(resp.body)
            resp.content_type = resource.content_type
            if not resp.content_type:
                resp.content_type = req.content_type


public_cors = CORS(allow_all_origins=True, allow_all_methods=True, allow_all_headers=True)
def CORSMiddleware():
    return public_cors.middleware


class DATAResources():
    def __init__(self, processor, failsafe):
        self.processor = processor
        if type(self.processor) != dict:
            self.processor = {
                'default': self.processor,
            }

        self.failsafe = failsafe
        self.on_get = self.process
        self.on_put = self.process
        self.on_post = self.process
        self.on_delete = self.process

    def resolve_processor(self, req, **kwargs):
        if req.method in self.processor:
            return self.processor[req.method]
        else:
            return self.processor['default']

    def process(self, req, resp, **kwargs):
        try:
            processor = self.resolve_processor(req)
            try:
                resp.data = processor(req.data, kwargs, req.params)
            except TypeError as e:
                resp.data = processor(req.data)
        except (falcon.HTTPError, falcon.HTTPStatus) as e:
            resp.data = {}
            raise e
        except Exception as e:
            logger.error('something went wrong with RPC:')
            logger.error(req.data)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = ''.join(traceback.format_exception(
                exc_type,
                exc_value,
                exc_traceback
            ))
            logger.error(stacktrace)
            raise falcon.HTTPInternalServerError()


class RAWResources():
    def __init__(self, processor, content_type):
        self.processor = processor
        self.content_type = content_type
    def on_post(self, req, resp, **kwargs):
        self.on_get(req, resp, **kwargs)
    def on_get(self, req, resp, **kwargs):
        try:
            try:
                resp.data = self.processor(req.data, kwargs, req.params)
            except TypeError as e:
                resp.data = self.processor(req.data)
        except Exception as e:
            logger.error('something went wrong with RPC:')
            logger.error(req.data)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            stacktrace = ''.join(traceback.format_exception(exc_type,
                                                               exc_value,
                                                               exc_traceback))
            logger.error(stacktrace)
            raise falcon.HTTPInternalServerError()


def make_service(pairs, middlewares=[]):
    service = falcon.API(middleware=middlewares)
    health_resources = RAWResources(lambda data: {'health': True}, 'text/html')
    service.add_route('/health', health_resources)
    for path, resource in pairs:
        service.add_route(path, resource)

    return service


def run_service(port, service):
    print('running services at port %d' % port)
    httpd = simple_server.make_server('0.0.0.0', port, service)
    httpd.serve_forever()
