# Task
You are given a list a of APIs and a user scenario. You task is to create a natural conversation between a user and an assistant that uses the APIs to complete the user's goal using the scenario as a guide.

The user should not mention or ask to use any tools or APIs. You should assume the user is not aware of the precise tools or APIs that would be required to complete their goal and is not interested in the details.

The assistant should use the APIs to complete the user's goal. If not enough information is provided by the user to call an API, the assistant should ask for more information. If this information is not provided in the scenario, then make up precise details for the user to say.

Each turn will consist of a user message, APIs used if any, and the assistants response. It is not necessary to call APIs on every turn, but a higher score will be assigned if multiple are used in a single turn. At least 5 APIs must be used by the end of the conversation. APIs can be re-used and do not need to be unique. The conversation should consist of at least 5 turns.

Deliver your response in this format:
```
- User: <user message>
- APIs used: <API1>, <API2>, ...
- Assistant: <assistant response>

- User: <user message>
- APIs used: <API1>, <API2>, ...
- Assistant: <assistant response>
...
```

# APIs
```
{{API_DOCS}}
```

# Scenario
{{QUERY}}

# Response
```
- User: 