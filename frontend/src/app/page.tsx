"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";

export default function Home() {
  // 渲染 workflow tool 调用
  useCopilotAction({
    name: "query_flight_and_generate_chart",
    description: "查询机票价格并生成图表",
    parameters: [
      {
        name: "query",
        type: "string",
        description: "用户的机票查询请求",
        required: true,
      },
    ],
    available: "disabled",  // 只渲染，不执行（后端执行）
    render: ({ args, status, result }) => {
      return (
        <div className="my-2 p-3 rounded-lg border border-blue-200 bg-blue-50 text-sm">
          <div className="flex items-center gap-2 font-medium text-blue-700">
            <span>🔧</span>
            <span>调用工具: query_flight_and_generate_chart</span>
            <span className={`ml-auto px-2 py-0.5 rounded text-xs ${status === "executing"
              ? "bg-yellow-100 text-yellow-700"
              : "bg-green-100 text-green-700"
              }`}>
              {status === "executing" ? "执行中..." : status === "complete" ? "完成" : status}
            </span>
          </div>

          {args?.query && (
            <div className="mt-2 text-blue-600">
              <span className="font-medium">查询:</span> {args.query}
            </div>
          )}

          {status === "complete" && result && (
            <div className="mt-2 text-green-700">
              <span className="font-medium">结果:</span>
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
          title: "✈️ 机票价格查询助手",
          initial: "👋 你好！我是机票价格查询助手。\n\n告诉我你想查询哪条航线的机票，我会帮你查询价格并生成图表。",
        }}
        suggestions={[
          {
            title: "北京 → 东京",
            message: "帮我查一下北京到东京的机票价格",
          },
          {
            title: "上海 → 纽约",
            message: "查询上海到纽约的机票多少钱",
          },
          {
            title: "广州 → 新加坡",
            message: "广州飞新加坡的机票价格是多少",
          },
        ]}
      />
    </main>
  );
}