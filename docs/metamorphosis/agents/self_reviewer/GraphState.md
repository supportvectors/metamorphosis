### GraphState

::: metamorphosis.agents.self_reviewer.state.GraphState

## Fields

- `original_text`: input provided by the user
- `copy_edited_text`: improved text from the copy editor
- `summary`: the short summary
- `word_cloud_path`: image path returned by the word cloud tool
- `achievements`: structured achievements list
- `review_scorecard`: structured evaluation
- `messages`: conversation messages for agent/tool steps
- `review_complete`: True when we have enough achievements

## State diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#e0f2ff', 'edgeLabelBackground':'#ffffffaa', 'clusterBkg':'#f7fbff', 'fontFamily':'Inter'}}}%%
stateDiagram-v2
    [*] --> Initialized
    Initialized --> CopyEditing: User submits text
    CopyEditing --> ParallelProcessing: Text edited

    state ParallelProcessing {
        [*] --> Summarizing
        [*] --> WordCloudGen
        Summarizing --> SummaryComplete
        WordCloudGen --> WordCloudComplete
        SummaryComplete --> [*]
        WordCloudComplete --> [*]
    }

    ParallelProcessing --> Achievements
    Achievements --> Evaluation
    Evaluation --> Complete
    Complete --> [*]
```



