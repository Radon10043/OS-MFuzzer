# Environment variables set

Create a `.env` file under the root of repository, program will read some environment variables during running. Here are involved environment variables:

| Environment Variable Name |                      Description                      |
| :-----------------------: | :---------------------------------------------------: |
|      OPENAI_API_KEY       |        API key to query LLM provided by OpenAI        |
|      OPENAI_API_BASE      |          Base url of LLM provided by OpenAI           |
|        CA_API_KEY         |     API key to query LLM provided by third-party      |
|    CA_OPENAI_API_BASE     |        Base url of LLM provided by third-party        |
|  GOOGLE_OPENAI_API_BASE   |          Google's openai compatible base url          |
|      GOOGLE_API_KEY       |        API key to query LLM provided by Google        |
|          PROJECT          |            Absolute path of the repository            |
|        EMAIL_HOST         |       Email-related environment variables, host       |
|        EMAIL_PORT         |       Email-related environment variables, port       |
|       EMAIL_SENDER        |  Email-related environment variables, sender's email  |
|      EMAIL_PASSWORD       | Email-related environment variables, email's password |