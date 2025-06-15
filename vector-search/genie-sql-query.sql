WITH search_results AS (
    SELECT * FROM VECTOR_SEARCH(
        index => 'users.david_hurley.vehicle_warranty_vs_index', 
        query_text => :user_question,
        num_results => 3
    )
)
SELECT 
    ai_query(
        "databricks-llama-4-maverick",
        "The user is asking a question about vehicle warrnty." ||
        "Answer the user question using the Question and Warranty Information." || 
        "Only answer the question and do not add extra warranty information that is unrelated" ||
        concat_ws('\n', 'Question: ', :user_question, '\n', 'Warranty Information: ', collect_list(chunked_markdown))
    ) as ai_answer
FROM 
    search_results
