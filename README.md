### xml-sparql-xml

This repo is to convert a question in xml to a SPARQL query, and then convert the query results back to a xml.

The rules are created based on the sample from [simplified-query-v1.0](https://www.dropbox.com/preview/gaia-ta2/simplified-query/version-1.0/simplified-query-v1.0.xml?role=personal) and [simplified-response-v1.0](https://www.dropbox.com/preview/gaia-ta2/simplified-query/version-1.0/simplified-response-v1.0.xml?role=personal), and the AIF version is [https://github.com/fatestigma/AIDA-Interchange-Format/tree/731fcb422b7c2b14b40abe7203ce29222076197a]

To use it, the `example/ontology_mapping.json` and `example/xml_mapping.json` has to be completed. And the code may have to be updated if complex mapping rules were added.

#### How to use it:
(See a full example in example/example.py)

1. set your input paths and database query endpoint:
    ```
    xml_tag_to_predicate = './ontology_mapping.json'
    predicate_to_xml_tag = './xml_mapping.json'
    xml_question = './question1.xml'
    endpoint = 'http://gaiadev01.isi.edu:3030/dryrun_all/query'
    ```

2. init a question:
    ```
    from src.Question import Question
    question = Question(xml_tag_to_predicate, xml_question)
    ```

3. convert the question to SPARQL query, query the database, and construct xml results:
    ```
    from src.QueryWrapper import QueryWrapper
    query_wrapper = QueryWrapper(endpoint, predicate_to_xml_tag)
    xml_response = query_wrapper.ask(question)
    ```

4. write the xml_results to a file:
    ```
    from src.utils import write_file
    write_file('./output.xml', xml_response)
    ```




