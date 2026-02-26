// State of the agent, make sure this aligns with your agent's state.
// This matches the session state structure used by ReviewAgent in agent.py
export type AgentState = {
  original_text?: string;
  reviewed_text?: string;
  summarized_text?: string;
  wordcloud_path?: string;
  achievements?: {
    items?: Array<{
      title: string;
      outcome: string;
      impact_area: string;
      metric_strings?: string[];
      timeframe?: string;
      ownership_scope?: string;
      collaborators?: string[];
      contribution?: string;
      rationale?: string;
      project_name?: string;
      project_text?: string;
      project_department?: string;
      project_impact_category?: string;
      project_effort_size?: string;
    }>;
    size?: number;
    unit?: string;
  };
  evaluation?: {
    metrics?: Array<{
      name: string;
      score: number;
      rationale: string;
      suggestion: string;
    }>;
    overall?: number;
    verdict?: string;
    notes?: string[];
    radar_labels?: string[];
    radar_values?: number[];
  };
  review_complete?: boolean;
};