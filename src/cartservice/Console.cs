using System.Diagnostics;
using Grpc.Core;
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

namespace cartservice
{
    internal class ConsoleTest
    {
        internal static object Run()
	{
	    using var openTelemetry = Sdk.CreateTracerProviderBuilder()
		.AddAspNetCoreInstrumentation()
		.AddConsoleExporter()
		.Build();
	    return null;
	}
    }
}
