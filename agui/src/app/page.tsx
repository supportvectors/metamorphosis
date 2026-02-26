"use client";

// The SelfReviewInterface components handles rendering of the main tabbed layout for self-review.
import { SelfReviewInterface } from "@/components/self-review";
// Import our shared AgentState types which corresponds to the agent's Python state declaration
import { AgentState } from "@/lib/types";
// CopilotKit hooks and components needed specifically for Agent interaction
import { useCoAgent } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";

export default function CopilotKitPage() {
  // Wrap our main content in the CopilotSidebar component.
  // This automatically provides a chat interface bound to the CopilotKit context.
  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <CopilotSidebar
        disableSystemMessage={false}
        clickOutsideToClose={false}
        defaultOpen={false}
        labels={{
          title: "Self-Review Assistant",
          initial:
            "👋 Hi! I'm your self-review assistant. I can help you process your review text, extract achievements, and evaluate your review quality.",
        }}
        // Define pre-configured questions that the user can use to kickstart or query their process
        suggestions={[
          {
            title: "Process Review",
            message:
              "Please process my review text and extract achievements, generate a summary, and evaluate the review.",
          },
          {
            title: "Check Status",
            message: "What is the current status of my review processing?",
          },
          {
            title: "View Achievements",
            message: "Show me the extracted achievements from my review.",
          },
          {
            title: "View Scorecard",
            message: "Show me the review scorecard and evaluation metrics.",
          },
        ]}
      >
        <YourMainContent />
      </CopilotSidebar>
    </div>
  );
}

function YourMainContent() {
  // 🪁 Shared State integration via CopilotKit's useCoAgent hook.
  // This hook wires our local React state directly to the Python agent's state.
  // CRITICAL: The name "text_review_agent" MUST match the name property of the LlmAgent initialized in your backend Python code (e.g. self_reviewer_gadk/agent.py)
  const { state, setState } = useCoAgent<AgentState>({
    name: "text_review_agent",
    // initialState defines the default values before the agent begins processing
    initialState: {
      original_text: "",
      reviewed_text: undefined,
      summarized_text: undefined,
      wordcloud_path: undefined,
      achievements: undefined,
      evaluation: undefined,
      review_complete: undefined,
    },
  });

  return (
    <div className="min-h-screen bg-background py-12 px-4 sm:px-6 lg:px-8 transition-colors duration-300">
      <SelfReviewInterface state={state} setState={setState} />
    </div>
  );
}
