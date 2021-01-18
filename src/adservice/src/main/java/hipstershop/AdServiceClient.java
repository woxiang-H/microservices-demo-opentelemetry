/*
 * Copyright 2018, Google LLC.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package hipstershop;

import hipstershop.Demo.Ad;
import hipstershop.Demo.AdRequest;
import hipstershop.Demo.AdResponse;
import io.grpc.ClientInterceptor;
import io.grpc.Metadata;
import io.grpc.Channel;
import io.grpc.CallOptions;
import io.grpc.ClientCall;
import io.grpc.ForwardingClientCall;
import io.grpc.MethodDescriptor;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;
import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.StatusCode;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.trace.propagation.HttpTraceContext;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import io.opentelemetry.context.propagation.DefaultContextPropagators;
import io.opentelemetry.context.propagation.TextMapPropagator;
import io.opentelemetry.exporter.logging.LoggingSpanExporter;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.trace.TracerSdkManagement;
import io.opentelemetry.sdk.trace.export.SimpleSpanProcessor;
import java.util.concurrent.TimeUnit;
import javax.annotation.Nullable;
import org.apache.logging.log4j.Level;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** A simple client that requests ads from the Ads Service. */
public class AdServiceClient {

  private static final Logger logger = LogManager.getLogger(AdServiceClient.class);
  private final String serverHostname;
  private final Integer serverPort;
  private final ManagedChannel channel;
  private final hipstershop.AdServiceGrpc.AdServiceBlockingStub blockingStub;

  OpenTelemetry openTelemetry = OpenTelemetry.get();
  Tracer tracer = openTelemetry.getTracer("AdService");
  TextMapPropagator textFormat = openTelemetry.getPropagators().getTextMapPropagator();
  TextMapPropagator.Setter<Metadata> setter =
      (carrier, key, value) ->
          carrier.put(Metadata.Key.of(key, Metadata.ASCII_STRING_MARSHALLER), value);

  /** Construct client connecting to Ad Service at {@code host:port}. */
  public AdServiceClient(String host, int port) {
    this.serverHostname = host;
    this.serverPort = port;
    this.channel = 
        ManagedChannelBuilder.forAddress(host, port)
            // Channels are secure by default (via SSL/TLS). For the example we disable TLS to avoid
            // needing certificates.
            .usePlaintext()
	    .intercept(new OpenTelemetryClientInterceptor())
            .build();
    blockingStub = hipstershop.AdServiceGrpc.newBlockingStub(channel);
  }

  /** Construct client for accessing RouteGuide server using the existing channel. */
  // private AdServiceClient(ManagedChannel channel) {
  //   this.channel = channel;
  //   blockingStub = hipstershop.AdServiceGrpc.newBlockingStub(channel);
  // }

  public void shutdown() throws InterruptedException {
    channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
  }

  /** Get Ads from Server. */
  public void getAds(String contextKey) {
    logger.info("Get Ads with context " + contextKey + " ...");
    AdRequest request = AdRequest.newBuilder().addContextKeys(contextKey).build();
    AdResponse response;

    Span span =
        tracer.spanBuilder("AdsClient").setSpanKind(Span.Kind.CLIENT).startSpan();
    span.setAttribute("component", "grpc");
    span.setAttribute("rpc.service", "AdService");
    span.setAttribute("net.peer.ip", this.serverHostname);
    span.setAttribute("net.peer.port", this.serverPort);
    try (Scope scope = span.makeCurrent()) {
      span.addEvent("Getting Ads");
      response = blockingStub.getAds(request);
      span.addEvent("Received response from Ads Service.");
    } catch (StatusRuntimeException e) {
      span.setStatus(StatusCode.ERROR, "gRPC status: " + e.getStatus());
      logger.log(Level.WARN, "RPC failed: " + e.getStatus());
      return;
    } finally {
      span.end();
    }
    for (Ad ads : response.getAdsList()) {
      logger.info("Ads: " + ads.getText());
    }
  }

  private static int getPortOrDefaultFromArgs(String[] args) {
    int portNumber = 9555;
    if (2 < args.length) {
      try {
        portNumber = Integer.parseInt(args[2]);
      } catch (NumberFormatException e) {
        logger.warn(String.format("Port %s is invalid, use default port %d.", args[2], 9555));
      }
    }
    return portNumber;
  }

  private static String getStringOrDefaultFromArgs(
      String[] args, int index, @Nullable String defaultString) {
    String s = defaultString;
    if (index < args.length) {
      s = args[index];
    }
    return s;
  }

  public class OpenTelemetryClientInterceptor implements ClientInterceptor {

    @Override
    public <ReqT, RespT> ClientCall<ReqT, RespT> interceptCall(
        MethodDescriptor<ReqT, RespT> methodDescriptor, CallOptions callOptions, Channel channel) {
      return new ForwardingClientCall.SimpleForwardingClientCall<ReqT, RespT>(
          channel.newCall(methodDescriptor, callOptions)) {
        @Override
        public void start(Listener<RespT> responseListener, Metadata headers) {
          textFormat.inject(Context.current(), headers, setter);
          super.start(responseListener, headers);
        }
      };
    }
  }

  private static void initTracing() {
    OpenTelemetry.setGlobalPropagators(
        DefaultContextPropagators.builder()
            .addTextMapPropagator(HttpTraceContext.getInstance())
            .build());

    LoggingSpanExporter exporter = new LoggingSpanExporter();
    TracerSdkManagement tracerProvider = OpenTelemetrySdk.getGlobalTracerManagement();
    tracerProvider.addSpanProcessor(SimpleSpanProcessor.builder(exporter).build());
  }

  /**
   * Ads Service Client main. If provided, the first element of {@code args} is the context key to
   * get the ads from the Ads Service
   */
  public static void main(String[] args) throws InterruptedException {
    // Add final keyword to pass checkStyle.
    final String contextKeys = getStringOrDefaultFromArgs(args, 0, "camera");
    final String host = getStringOrDefaultFromArgs(args, 1, "localhost");
    final int serverPort = getPortOrDefaultFromArgs(args);

    initTracing();

    AdServiceClient client = new AdServiceClient(host, serverPort);
    try {
      client.getAds(contextKeys);
    } finally {
      client.shutdown();
    }

    logger.info("Exiting AdServiceClient...");
  }
}
