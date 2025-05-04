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
          {/* Video Tutorial at the top of the card */}
          <div className="flex flex-col items-center mb-6">
            <span style={{ background: '#e6f0fa', color: '#1e3a8a', fontWeight: 600, fontSize: '1rem', borderRadius: '9999px', padding: '0.5rem 1.5rem', display: 'inline-flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.9rem', boxShadow: '0 2px 8px 0 rgba(30,58,138,0.07)' }}>
              <svg xmlns="http://www.w3.org/2000/svg" style={{ color: '#2563eb', width: '1.3em', height: '1.3em' }} fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="10" stroke="#2563eb" strokeWidth="2" fill="#fff"/><path stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01"/></svg>
              Watch the Tutorial: <span style={{fontWeight:700}}>Click the video below for a quick walkthrough</span>
            </span>
            <div className="shadow-xl border-4 border-transparent bg-gradient-to-br from-blue-50 to-white overflow-visible animate-glow w-full flex flex-col items-center pt-6 pb-4 rounded-xl">
              <div className="flex flex-col items-center">
                <div className="text-xl font-bold text-blue-800 mb-2 flex items-center gap-2">
                  {/* Removed video camera icon */}
                </div>
                <div className="mb-2 text-base font-semibold text-purple-700">Get started in under 3 minutes!</div>
                <video
                  className="rounded-xl shadow-2xl border-4 border-blue-300 max-w-full w-[350px] md:w-[500px] transition-transform hover:scale-105 hover:shadow-pink-200"
                  controls
                  poster="/public/logo_light.png"
                >
                  <source src="/public/tutorial.mp4" type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
                <div className="text-gray-700 text-sm mt-3">See how to get started and make the most of the content generator.</div>
              </div>
            </div>
          </div>
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
