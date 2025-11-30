import {
    CopilotRuntime,
    ExperimentalEmptyAdapter,
    copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

// Backend URL - configurable via environment variable for Docker deployment
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// Service adapter for CopilotKit runtime
const serviceAdapter = new ExperimentalEmptyAdapter();

// Create CopilotRuntime with our Microsoft Agent Framework agent
const runtime = new CopilotRuntime({
    agents: {
        // Connect to our Python backend via AG-UI protocol
        flight_chart_agent: new HttpAgent({
            url: `${BACKEND_URL}/copilotkit`,
        }),
    },
});

// Export POST handler for the API route
export const POST = async (req: NextRequest) => {
    const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
        runtime,
        serviceAdapter,
        endpoint: "/api/copilotkit",
    });

    return handleRequest(req);
};
