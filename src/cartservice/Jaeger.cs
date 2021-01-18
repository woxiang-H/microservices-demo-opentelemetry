using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

namespace cartservice
{
    internal class JaegerExporter
    {
        internal static object Run(string host, int port)
        {
	    return RunWithActivity(host, port);
	}
	
	internal static object RunWithActivity(string host, int port)
	{
	    using var openTelemetry = Sdk.CreateTracerProviderBuilder()
		.SetResourceBuilder(ResourceBuilder.CreateDefault().AddService("cartservice"))
		.AddSource("Samples.SampleClient", "Samples.SampleServer")
		.AddJaegerExporter(o =>
		{
		    o.AgentHost = host;
		    o.AgentPort = port;
		})
		.Build();
	
	    return null;
	}
    }
}
