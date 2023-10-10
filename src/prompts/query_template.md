# Task
You will be provided with a list of APIs. These APIs will have a description, a list of tools it provides, descriptions of these tools, and the parameters and return types for each tool. Your task involves creating 10 varied, innovative, and detailed user queries that require multiple tool calls to complete from each API.

For instance, given the API "Hotels" with the tools "SearchHotels", "BookHotel", and "CancelBooking" and "NBA News" with the tools "GetNBANews". Your query should articulate something akin to:

"Did the Broncos make it into the playoffs? I want to watch them in person if so. Can you book a hotel for me in the city they're playing in?"

This query exemplifies how to utilize tools across all the APIs given to create a complex query that uses multiple tools. A query that fails to use tools from all APIs will not be accepted. Queries that require only a single tool call will also not be accepted.

Queries should not mention or ask to use any tools or APIs. For instance, the above query would be invalid if it directly asked to use the "Hotels" or "NBA News" API or any of their tools. The query should represent a natural goal that a user would have without knowledge of the precise tools or APIs that would be required to complete it.

Since there can potentially be many APIs, your query does not have to be short. However, it should be concise and clear. You should also provide a list of tools used in your query and the API they belong to. For instance, the query above would have the following list:

- GetNBANews (NBA News)
- SearchHotels (Hotels)
- BookHotel (Hotels)

Deliver your response in this format:
```json
[
	{"index": 1, "query": "<query1>", "apis_used": [{"api": "<api name>", "tool": "<tool name>"}, ...]},
	...
]
```

# APIs
{{API_DOCS}}

# Response
```json
[
	{"index": 1, "query": "