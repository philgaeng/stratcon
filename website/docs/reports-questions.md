## Reports Page Updates – Clarification Questions

1. How should the two main content columns be sized on desktop (e.g. 50/50, 60/40), and should they stack vertically on smaller breakpoints the way the current cards do?
   60/40
2. For the left column, do you want the existing “Generate Month Report” and “Generate Custom Report” cards to keep their current layout and behavior verbatim, just stacked one above the other inside that column?
   yes
3. Where should the list of buildings come from for the new “Generate Building Reports” section—does an API already exist (e.g. `api.getBuildings(...)`), and is it filtered by the currently selected client and/or tenant from the explorer?
   thats exactly it
4. When a building is selected in the new section, should that selection synchronize with the explorer/selection provider (similar to how client and tenant sync today), or stay local to the building reports panel?
   nope
5. Is the month picker in the building reports section required, optional, or should it default to a specific month (e.g. last complete month)? Should it reuse the same 12‑month dropdown model used by the custom report form?
   by default we will feed the current date to the API
6. Are the `generate_billing_info` and `generate_last_records` buttons meant to call new API endpoints? If so, what request payload (fields and naming) should each one send?
   yes - I let you suggest the naming
7. Should each of those buttons manage its own loading/disabled state and success/error messaging, or should they share the existing `successMessage` and `errorMessage` banners used by the other report generators?
   They can share if you believe it is a good setup
8. What copy should we display after a building report request is kicked off—same email notification message as the existing generators, or something different?
   same
9. Do we need any additional validation before enabling the building report buttons (e.g. require both building and month, check authentication again), or can we mirror the validations used elsewhere on the page?
   this will be managed by user_type
10. Are there any style variations (colors, icons, descriptive text) you’d like for the new building reports column, or should it follow the visual pattern of the existing cards?
    Lets follow the same pattern, will make it easier to amend
