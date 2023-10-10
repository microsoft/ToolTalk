# Task
You will be provided with a list of APIs. These APIs will have a description and a list of parameters and return types for each tool. Your task involves creating 3 varied, complex, and detailed user scenarios that require at least 5 API calls to complete involving at least 3 different APIs. One of these APIs will be explicitly provided and the other two will be chosen by you.

For instance, given the APIs: SearchHotels, BookHotel, CancelBooking, GetNFLNews. Given that GetNFLNews is explicitly provided, your scenario should articulate something akin to:

"The user wants to see if the Broncos won their last game (GetNFLNews). They then want to see if that qualifies them for the playoffs and who they will be playing against (GetNFLNews). The Broncos did make it into the playoffs, so the user wants watch the game in person. They want to look for hotels where the playoffs are occurring (GetNBANews + SearchHotels). After looking at the options, the user chooses to book a 3-day stay at the cheapest 4-star option (BookHotel)."

This scenario exemplifies a scenario using 5 API calls. The scenario is complex, detailed, and concise as desired. The scenario also includes two APIs used in tandem, the required API, GetNBANews to search for the playoffs location and SearchHotels to find hotels based on the returned location. Usage of multiple APIs in tandem is highly desirable and will receive a higher score. Ideally each scenario should contain one or more instances of multiple APIs being used in tandem.

Note that this scenario does not use all the APIs given and re-uses the "GetNBANews" API. Re-using APIs is allowed, but each scenario should involve at least 3 different APIs. Note that API usage is also included in the scenario, but exact parameters are not necessary. You must use a different combination of APIs for each scenario. All APIs must be used in at least one scenario. You can only use the APIs provided in the APIs section.

Note that API calls are not explicitly mentioned and their uses are included in parentheses. This behaviour should be mimicked in your response.

Deliver your response in this format:
```
- Scenario 1: <Scenario1>
- Scenario 2: <Scenario2>
- Scenario 3: <Scenario3>
```

# APIs
```
{{API_DOCS}}
```

# Response
Required API: {{REQUIRED_API}}
Scenarios with >=5 API calls:
```
- Scenario 1: