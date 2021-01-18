#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import random
import time
import traceback
from concurrent import futures

from google.auth.exceptions import DefaultCredentialsError
import grpc

from opentelemetry.instrumentation.grpc import server_interceptor
from opentelemetry import trace
from opentelemetry.exporter import zipkin
from opentelemetry.exporter import jaeger
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

import demo_pb2
import demo_pb2_grpc
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

from logger import getJSONLogger
logger = getJSONLogger('recommendationservice-server')

class RecommendationService(demo_pb2_grpc.RecommendationServiceServicer):
    def ListRecommendations(self, request, context):
        max_responses = 5
        # fetch list of products from product catalog stub
        cat_response = product_catalog_stub.ListProducts(demo_pb2.Empty())
        product_ids = [x.id for x in cat_response.products]
        filtered_products = list(set(product_ids)-set(request.product_ids))
        num_products = len(filtered_products)
        num_return = min(max_responses, num_products)
        # sample list of indicies to return
        indices = random.sample(range(num_products), num_return)
        # fetch product ids from indices
        prod_list = [filtered_products[i] for i in indices]
        logger.info("[Recv ListRecommendations] product_ids={}".format(prod_list))
        # build and return response
        response = demo_pb2.ListRecommendationsResponse()
        response.product_ids.extend(prod_list)
        return response

    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)

    def Watch(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.UNIMPLEMENTED)


if __name__ == "__main__":
    logger.info("initializing recommendationservice")

    # jaeger
    try:
      if "DISABLE_JAEGER" in os.environ:
        raise KeyError()
      else:
        logger.info("Jaeger enabled.")
        trace.set_tracer_provider(TracerProvider())
        url = os.environ.get('JAEGER_SERVICE_ADDR')
        jaeger_exporter = jaeger.JaegerSpanExporter(
          service_name="recommendationservice",
          collector_endpoint = url
        )
        span_processor = BatchExportSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        tracer_interceptor = server_interceptor(trace)
    except (KeyError, DefaultCredentialsError):
        logger.info("Jaeger disabled.")
    # zipkin
    try:
      if "DISABLE_ZIPKIN" in os.environ:
        raise KeyError()
      else:
        logger.info("Zipkin enabled.")
        trace.set_tracer_provider(TracerProvider())
        endpoint = os.environ.get('ZIPKIN_SERVICE_ADDR')
        zipkin_exporter = zipkin.ZipkinSpanExporter(
          service_name="recommendationservice",
          url = endpoint
        )
        span_processor = BatchExportSpanProcessor(zipkin_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        tracer_interceptor = server_interceptor(trace)
    except (KeyError, DefaultCredentialsError):
        logger.info("Zipkin disabled.")
        tracer_interceptor = server_interceptor()

    port = os.environ.get('PORT', "8080")
    catalog_addr = os.environ.get('PRODUCT_CATALOG_SERVICE_ADDR', '')
    if catalog_addr == "":
        raise Exception('PRODUCT_CATALOG_SERVICE_ADDR environment variable not set')
    logger.info("product catalog address: " + catalog_addr)
    channel = grpc.insecure_channel(catalog_addr)
    product_catalog_stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)

    # create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                      interceptors=(tracer_interceptor,))

    # add class to gRPC server
    service = RecommendationService()
    demo_pb2_grpc.add_RecommendationServiceServicer_to_server(service, server)
    health_pb2_grpc.add_HealthServicer_to_server(service, server)

    # start server
    logger.info("listening on port: " + port)
    server.add_insecure_port('[::]:'+port)
    server.start()

    # keep alive
    try:
         while True:
            time.sleep(10000)
    except KeyboardInterrupt:
            server.stop(0)
