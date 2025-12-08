"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";

export default function Home() {
  // Render workflow tool calls
  useCopilotAction({
    name: "query_flight_and_generate_chart",
    description: "Query flight prices and generate charts",
    parameters: [
      {
        name: "query",
        type: "string",
        description: "User's flight query request",
        required: true,
      },
    ],
    available: "disabled",  // Render only, execution happens on backend
    render: ({ args, status, result }) => {
      return (
        <div className="my-2 p-3 rounded-lg border border-blue-200 bg-blue-50 text-sm">
          <div className="flex items-center gap-2 font-medium text-blue-700">
            <span>🔧</span>
            <span>Tool: query_flight_and_generate_chart</span>
            <span className={`ml-auto px-2 py-0.5 rounded text-xs ${status === "executing"
              ? "bg-yellow-100 text-yellow-700"
              : "bg-green-100 text-green-700"
              }`}>
              {status === "executing" ? "Running..." : status === "complete" ? "Done" : status}
            </span>
          </div>

          {args?.query && (
            <div className="mt-2 text-blue-600">
              <span className="font-medium">Query:</span> {args.query}
            </div>
          )}

          {status === "complete" && result && (
            <div className="mt-2 text-green-700">
              <span className="font-medium">Result:</span>
              <div className="mt-1 p-2 bg-white rounded text-xs">
                {String(result)}
              </div>
            </div>
          )}
        </div>
      );
    },
  });

  return (
    <main className="h-screen w-screen">
      <CopilotChat
        className="h-full w-full"
        labels={{
          title: "✈️ Flight Price Assistant",
          initial: "👋 Hello! I'm your flight price assistant.\n\nTell me which route you'd like to check, and I'll query the prices and generate a chart for you.",
        }}
        suggestions={[
          {
            title: "Beijing → Tokyo",
            message: "Check the flight price from Beijing to Tokyo",
          },
          {
            title: "Shanghai → New York",
            message: "How much is a flight from Shanghai to New York?",
          },
          {
            title: "Guangzhou → Singapore",
            message: "What's the price for a flight from Guangzhou to Singapore?",
          },
        ]}
      />
    </main>
  );
}
