module github.com/GoogleCloudPlatform/microservices-demo/src/frontend

go 1.15

require (
	cloud.google.com/go v0.40.0
	github.com/golang/protobuf v1.3.1
	github.com/google/pprof v0.0.0-20190515194954-54271f7e092f // indirect
	github.com/google/uuid v1.1.1
	github.com/gorilla/mux v1.7.3
	github.com/konsorten/go-windows-terminal-sequences v1.0.2 // indirect
	github.com/pkg/errors v0.8.1
	github.com/sirupsen/logrus v1.4.2
	github.com/uber/jaeger-client-go v2.21.1+incompatible // indirect
	golang.org/x/net v0.0.0-20200707034311-ab3426394381
	golang.org/x/sys v0.0.0-20190626221950-04f50cda93cb // indirect
	google.golang.org/api v0.7.1-0.20190709010654-aae1d1b89c27 // indirect
	google.golang.org/appengine v1.6.1 // indirect
	google.golang.org/genproto v0.0.0-20190708153700-3bdd9d9f5532 // indirect
	google.golang.org/grpc v1.33.2
	go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp v0.13.0
	go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc v0.13.0
	go.opentelemetry.io/otel/exporters/trace/jaeger v0.13.0
	go.opentelemetry.io/otel/exporters/trace/zipkin v0.13.0
	go.opentelemetry.io/otel v0.13.0
	go.opentelemetry.io/otel/exporters/stdout v0.13.0
	go.opentelemetry.io/otel/sdk v0.13.0
)
