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

import grpc

import demo_pb2
import demo_pb2_grpc

from logger import getJSONLogger
logger = getJSONLogger('emailservice-client')

from opentelemetry.instrumentation.grpc import client_interceptor
from opentelemetry import trace
from opentelemetry.exporter import zipkin
from opentelemetry.exporter import jaeger
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

# jaeger
try:
  if "DISABLE_JAEGER" in os.environ:
    raise KeyError()
  else:
    logger.info("Jaeger enabled.")
    trace.set_tracer_provider(TracerProvider())
    url = os.environ.get('JAEGER_SERVICE_ADDR')
    jaeger_exporter = jaeger.JaegerSpanExporter(
      service_name="emailservice",
      collector_endpoint = url
    )
    span_processor = BatchExportSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    tracer_interceptor = client_interceptor(trace)
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
      service_name="emailservice",
      url = endpoint
    )
    span_processor = BatchExportSpanProcessor(zipkin_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    tracer_interceptor = client_interceptor(trace)
except (KeyError, DefaultCredentialsError):
    logger.info("Zipkin disabled.")
    tracer_interceptor = client_interceptor()

def send_confirmation_email(email, order):
  channel = grpc.insecure_channel('0.0.0.0:8080')
  channel = grpc.intercept_channel(channel, tracer_interceptor)
  stub = demo_pb2_grpc.EmailServiceStub(channel)
  try:
    response = stub.SendOrderConfirmation(demo_pb2.SendOrderConfirmationRequest(
      email = email,
      order = order
    ))
    logger.info('Request sent.')
  except grpc.RpcError as err:
    logger.error(err.details())
    logger.error('{}, {}'.format(err.code().name, err.code().value))

if __name__ == '__main__':
  logger.info('Client for email service.')
