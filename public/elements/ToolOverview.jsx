import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const tools = [
	{
		icon: (
			<img
				src="/public/content.svg"
				alt="Web & App Content"
				className="h-7 w-7"
			/>
		), // Web & App
		name: "Web & App Content Creation",
		description:
			"Create compelling content for Riyadh Air's digital platforms, including engaging landing pages, informative feature descriptions, and clear UI text to enhance user experience.",
		color: "bg-blue-50 dark:bg-blue-900/40",
	},
	{
		icon: (
			<img
				src="/public/lifecycle.svg"
				alt="Lifecycle Content"
				className="h-7 w-7"
			/>
		), // Lifecycle
		name: "Lifecycle Content Creation",
		description:
			"Create dynamic content such as emails, push notifications, and SMS messages to support various stages of the customer lifecycle with Riyadh Air.",
		color: "bg-green-50 dark:bg-green-900/40",
	},
	{
		icon: <img src="/public/policy.svg" alt="RX Policy" className="h-7 w-7" />, // RX Policy
		name: "RX Policy Generation",
		description:
			"Draft, review, and generate policy documents and regulatory content for Riyadh Air, ensuring compliance and clarity.",
		color: "bg-purple-50 dark:bg-purple-900/40",
	},
	{
		icon: <img src="/public/refine.svg" alt="Content Refinement" className="h-7 w-7" />, // Refine
		name: "Content Refinement",
		description:
			"Polish, edit, and enhance existing content for Riyadh Air to improve clarity, tone, and effectiveness.",
		color: "bg-orange-50 dark:bg-orange-900/40",
	},
	{
		icon: <img src="/public/translator.svg" alt="Content Translation" className="h-7 w-7" />, // Translation
		name: "Content Translation",
		description:
			"Translate Riyadh Air's content into modern standard Arabic, preserving Riyadh Air’s brand tone, style and Arabic lexicon.",
		color: "bg-teal-50 dark:bg-teal-900/40",
	},
];

export default function ToolOverview() {
	// Use the globally injected `props` object if needed (do not take as argument)
	return (
		<div className="welcome-tool-overview max-w-2xl mx-auto py-8 px-4">
			<Card className="mb-6 shadow-md border-2 border-blue-100 dark:border-blue-900 bg-white dark:bg-gray-900">
				<CardHeader className="flex flex-row items-center gap-3">
					<img
						src="/public/avatars/riyadh_air.jpg"
						alt="Help"
						className="h-6 w-6 text-blue-500 rounded-full object-cover"
					/>
					<CardTitle className="text-lg font-semibold text-gray-900 dark:text-gray-100">
						Welcome to the Riyadh Air Content Generator!
					</CardTitle>
				</CardHeader>
				<CardContent>
					{/* Video Tutorial at the top of the card */}
					<div className="flex flex-col items-center mb-6">
						<span className="inline-flex items-center gap-2 mb-3 px-6 py-2 rounded-full font-semibold text-blue-800 dark:text-blue-200 bg-blue-50 dark:bg-blue-900/40 shadow">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								className="text-blue-600 dark:text-blue-300"
								style={{ width: "1.3em", height: "1.3em" }}
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<circle
									cx="12"
									cy="12"
									r="10"
									stroke="currentColor"
									strokeWidth="2"
									fill="white"
									className="dark:fill-gray-900"
								/>
								<path
									stroke="currentColor"
									strokeWidth="2"
									strokeLinecap="round"
									strokeLinejoin="round"
									d="M12 8v4m0 4h.01"
								/>
							</svg>
							Watch the Tutorial:{" "}
							<span className="font-bold">
								Click the video below for a quick walkthrough
							</span>
						</span>
						<div className="shadow-xl border-4 border-transparent bg-gradient-to-br from-blue-50 to-white dark:from-blue-900/40 dark:to-gray-900 overflow-visible animate-glow w-full flex flex-col items-center pt-6 pb-4 rounded-xl">
							<div className="flex flex-col items-center">
								<div className="text-xl font-bold text-blue-800 dark:text-blue-200 mb-2 flex items-center gap-2">
									{/* Removed video camera icon */}
								</div>
								<div className="mb-2 text-base font-semibold text-purple-700 dark:text-purple-200">
									Get started in under 4 minutes!
								</div>
								<video
									className="rounded-xl shadow-2xl border-4 border-blue-300 dark:border-blue-800 max-w-full w-[350px] md:w-[500px] transition-transform hover:scale-105 hover:shadow-pink-200"
									controls
									poster="/public/logo_light.png"
								>
									<source src="/public/tutorial.mp4" type="video/mp4" />
									Your browser does not support the video tag.
								</video>
								<div className="text-gray-700 dark:text-gray-300 text-sm mt-3">
									See how to get started and make the most of the content
									generator.
								</div>
							</div>
						</div>
					</div>
					<p className="text-gray-700 dark:text-gray-200 mb-2">
						This app provides 5 specialized tools to help you generate, refine,
						and translate content for Riyadh Air. Use the{" "}
						<span className="font-semibold text-blue-600 dark:text-blue-300">
							tool picker dropdown
						</span>{" "}
						at the top left of the chat to select the tool that best fits your
						needs.
					</p>
					<ul className="list-disc pl-6 text-gray-600 dark:text-gray-300 text-sm">
						<li>Switch between tools at any time using the dropdown.</li>
						<li>Each tool offers a unique workflow and tailored prompts.</li>
						<li>Starter prompts and forms will guide you for each tool.</li>
					</ul>
				</CardContent>
			</Card>
			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				{tools.map((tool, idx) => {
					// Pick a readable title color for each card in dark mode
					const darkTitleColors = [
						'dark:text-blue-200',
						'dark:text-green-200',
						'dark:text-purple-200',
						'dark:text-orange-200',
						'dark:text-teal-200'
					];
					return (
						<Card
							key={tool.name}
							className={`flex flex-row items-start gap-4 p-4 ${tool.color} border-0 shadow-sm`}
						>
							<div className="mt-1">{tool.icon}</div>
							<div>
								<div
									className={`font-semibold text-base mb-1 text-gray-900 ${darkTitleColors[idx]}`}
								>
									{tool.name}
								</div>
								<div className="text-gray-700 dark:text-gray-300 text-sm">
									{tool.description}
								</div>
							</div>
						</Card>
					);
				})}
			</div>
			<div className="mt-8 text-center text-gray-500 dark:text-gray-400 text-xs">
				Need help? Select the{" "}
				<span className="font-semibold">
					"Welcome / Tool Overview"
				</span>{" "}
				profile anytime for guidance.
			</div>
		</div>
	);
}
