### xml-sparql-xml

This repo is to convert a question in xml to a SPARQL query, and then convert the query results back to a xml.

#### How to use it:
(See a full example in example/example.py)

1. init a question:
    ```
    from src.Question import Question
    xml = 'sample_xml_query.xml'
    # xml can be either a filepath to xml file or a string of xml
    q = Question(xml)
    ```

2. init a Answer with Question q, and then call `ask()`, it will return the xml response in string
    ```
    from src.Answer import Answer
    ans = Answer(q)
    response = ans.ask()
    ```

* __you may want to change the query endpoint in `src/utils.py`__



