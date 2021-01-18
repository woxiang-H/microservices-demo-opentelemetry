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

from concurrent import futures
import argparse
import os
import sys
import time
import grpc
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateError
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import DefaultCredentialsError

import demo_pb2
import demo_pb2_grpc
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

from opentelemetry.instrumentation.grpc import server_interceptor
from opentelemetry import trace
from opentelemetry.exporter import zipkin
from opentelemetry.exporter import jaeger
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor

# import googleclouddebugger
import googlecloudprofiler

from logger import getJSONLogger
logger = getJSONLogger('emailservice-server')

# try:
#     googleclouddebugger.enable(
#         module='emailserver',
#         version='1.0.0'
#     )
# except:
#     pass

# Loads confirmation email template from file
env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
template = env.get_template('confirmation.html')

class BaseEmailService(demo_pb2_grpc.EmailServiceServicer):
  def Check(self, request, context):
    return health_pb2.HealthCheckResponse(
      status=health_pb2.HealthCheckResponse.SERVING)

class EmailService(BaseEmailService):
  def __init__(self):
    raise Exception('cloud mail client not implemented')
    super().__init__()

  @staticmethod
  def send_email(client, email_address, content):
    response = client.send_message(
      sender = client.sender_path(project_id, region, sender_id),
      envelope_from_authority = '',
      header_from_authority = '',
      envelope_from_address = from_address,
      simple_message = {
        "from": {
          "address_spec": from_address,
        },
        "to": [{
          "address_spec": email_address
        }],
        "subject": "Your Confirmation Email",
        "html_body": content
      }
    )
    logger.info("Message sent: {}".format(response.rfc822_message_id))

  def SendOrderConfirmation(self, request, context):
    email = request.email
    order = request.order

    try:
      confirmation = template.render(order = order)
    except TemplateError as err:
      context.set_details("An error occurred when preparing the confirmation mail.")
      logger.error(err.message)
      context.set_code(grpc.StatusCode.INTERNAL)
      return demo_pb2.Empty()

    try:
      EmailService.send_email(self.client, email, confirmation)
    except GoogleAPICallError as err:
      context.set_details("An error occurred when sending the email.")
      print(err.message)
      context.set_code(grpc.StatusCode.INTERNAL)
      return demo_pb2.Empty()

    return demo_pb2.Empty()

class DummyEmailService(BaseEmailService):
  def SendOrderConfirmation(self, request, context):
    logger.info('A request to send order confirmation email to {} has been received.'.format(request.email))
    return demo_pb2.Empty()

class HealthCheck():
  def Check(self, request, context):
    return health_pb2.HealthCheckResponse(
      status=health_pb2.HealthCheckResponse.SERVING)

def start(dummy_mode):
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),
                       interceptors=(tracer_interceptor,))
  service = None
  if dummy_mode:
    service = DummyEmailService()
  else:
    raise Exception('non-dummy mode not implemented yet')

  demo_pb2_grpc.add_EmailServiceServicer_to_server(service, server)
  health_pb2_grpc.add_HealthServicer_to_server(service, server)

  port = os.environ.get('PORT', "8080")
  logger.info("listening on port: "+port)
  server.add_insecure_port('[::]:'+port)
  server.start()
  try:
    while True:
      time.sleep(3600)
  except KeyboardInterrupt:
    server.stop(0)


if __name__ == '__main__':
  logger.info('starting the email service in dummy mode.')

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
        service_name="emailservice",
        url = endpoint
      )
      span_processor = BatchExportSpanProcessor(zipkin_exporter)
      trace.get_tracer_provider().add_span_processor(span_processor)
      tracer_interceptor = server_interceptor(trace)
  except (KeyError, DefaultCredentialsError):
      logger.info("Zipkin disabled.")
      tracer_interceptor = server_interceptor()

  start(dummy_mode = True)
