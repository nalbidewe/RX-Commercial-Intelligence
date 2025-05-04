import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const tools = [
  {
    icon: <img src="/public/content.svg" alt="Web & App Content" className="h-7 w-7" />, // Web & App
    name: "Web & App Content Creation",
    description: "Generate engaging and tailored website and application content for Riyadh Air, including landing pages, feature descriptions, and user interface text.",
    color: "bg-blue-50"
  },
  {
    icon: <img src="/public/lifecycle.svg" alt="Lifecycle Content" className="h-7 w-7" />, // Lifecycle
    name: "Lifecycle Content Creation",
    description: "Create comprehensive lifecycle content for Riyadh Air, such as onboarding flows, customer journey communications, and process documentation.",
    color: "bg-green-50"
  },
  {
    icon: <img src="/public/policy.svg" alt="RX Policy" className="h-7 w-7" />, // RX Policy
    name: "RX Policy Generation",
    description: "Draft, review, and generate policy documents and regulatory content for Riyadh Air, ensuring compliance and clarity.",
    color: "bg-purple-50"
  },
  {
    icon: <img src="/public/refine.svg" alt="Content Refinement" className="h-7 w-7" />, // Refine
    name: "Content Refinement",
    description: "Polish, edit, and enhance existing content for Riyadh Air to improve clarity, tone, and effectiveness.",
    color: "bg-orange-50"
  },
  {
    icon: <img src="/public/translator.svg" alt="Content Translation" className="h-7 w-7" />, // Translation
    name: "Content Translation",
    description: "Translate Riyadh Air's content into modern standard Arabic, maintaining brand voice and cultural relevance.",
    color: "bg-teal-50"
  }
];

export default function ToolOverview() {
  // Use the globally injected `props` object if needed (do not take as argument)
  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <Card className="mb-6 shadow-md border-2 border-blue-100">
        <CardHeader className="flex flex-row items-center gap-3">
          <img src="/public/avatars/riyadh_air.jpg" alt="Help" className="h-6 w-6 text-blue-500 rounded-full object-cover" />
          <CardTitle className="text-lg font-semibold">Welcome to the Riyadh Air Content Generator!</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-700 mb-2">
            This app provides 5 specialized tools to help you generate, refine, and translate content for Riyadh Air. Use the <span className="font-semibold text-blue-600">tool picker dropdown</span> at the top left of the chat to select the tool that best fits your needs.
          </p>
          <ul className="list-disc pl-6 text-gray-600 text-sm">
            <li>Switch between tools at any time using the dropdown.</li>
            <li>Each tool offers a unique workflow and tailored prompts.</li>
            <li>Starter prompts and forms will guide you for each tool.</li>
          </ul>
        </CardContent>
      </Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools.map((tool, idx) => (
          <Card key={tool.name} className={`flex flex-row items-start gap-4 p-4 ${tool.color} border-0 shadow-sm`}>
            <div className="mt-1">{tool.icon}</div>
            <div>
              <div className="font-semibold text-base mb-1">{tool.name}</div>
              <div className="text-gray-700 text-sm">{tool.description}</div>
            </div>
          </Card>
        ))}
      </div>
      <div className="mt-8 text-center text-gray-500 text-xs">
        Need help? Select the <span className="font-semibold">"Welcome / Tool Overview"</span> profile anytime for guidance.
      </div>
    </div>
  );
}
