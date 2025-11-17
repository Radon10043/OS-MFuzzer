# Environment Variables

Create a `.env` file in the root of the repository. The program will read these environment variables at runtime. The following variables are supported:

| Variable Name            | Description                                           |
| :----------------------- | :---------------------------------------------------- |
| `OPENAI_API_KEY`         | API key for the OpenAI LLM.                           |
| `OPENAI_API_BASE`        | Base URL for the OpenAI LLM.                          |
| `CA_API_KEY`             | API key for a third-party LLM.                        |
| `CA_OPENAI_API_BASE`     | Base URL for a third-party LLM.                       |
| `GOOGLE_OPENAI_API_BASE` | Google's OpenAI-compatible base URL.                  |
| `GOOGLE_API_KEY`         | API key for the Google LLM.                           |
| `PROJECT`                | The absolute path to the repository.                  |
| `EMAIL_HOST`             | Host for the email server.                            |
| `EMAIL_PORT`             | Port for the email server.                            |
| `EMAIL_SENDER`           | Sender's email address.                               |
| `EMAIL_PASSWORD`         | Password for the sender's email account.              |