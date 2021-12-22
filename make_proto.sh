python -m grpc_tools.protoc -I./protos --python_out=./src/opentelemetry/exporter/digma --grpc_python_out=./src/opentelemetry/exporter/digma ./protos/collector.proto
