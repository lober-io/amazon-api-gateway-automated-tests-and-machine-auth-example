# Automated API testing, performance testing and Machine-to-Machine authentication with Amazon API Gateway

This repository showcases end-to-end implementation of API including Performance Testing, Automated Testing, and Machine-to-Machine authentication.

The use cases are:

- Automated API Testing Pipeline with AWS CodePipeline, AWS CodeBuild, and Newman
- Generate test reports CodeBuild Reports and the Newman xunit Reporter
- Performance testing your API and multiple backend types with Postman and K6
- Machine-to-Machine authentication with an Amazon Cognito User Pool (OAuth 2.0 Client credentials grant) and Amazon API Gateway - Cognito Authorizer

My blog posts on API Performance Testing, Automated API Testing, and Machine-to-Machine authentication include code snippets. Please refer to them for more information.
- [Unveiling the Power of Amazon API Gateway: A Comparative Analysis of Service Integrations and Lambda Functions](https://medium.com/@fabian_lober/the-cost-efficiency-and-speed-of-amazon-api-gateway-service-integration-4ad241ff71e3)
- To be released
- To be released

This example creates **ongoing** costs! To reduce these, you can comment out the EC2 stack in `app.py`. 

All resources and configurations are provided through AWS CDK v2 in Python.

## Architecture

### AWS

**TBD**

### API

#### Available Endpoints
- GET /books
- POST /books
- GET /books/<bookId>
- PUT /books/<bookId>
- DELETE /books/<bookId>



## Prerequisites / Requirements 

**This example was developed and tested on Mac only.**

You need at least:
- Python 3.10
- CDK v2
- node 16 or higher

The following tools are optional:
- Postman
- newman
- newman-reporter-html
- newman newman-reporter-xunit
- k6

## Get started

1. Fork the Github repository

Log into your GitHub account and fork the following repository: [amazon-api-gateway-automated-tests-and-machine-auth-example](https://github.com/lober-io/amazon-api-gateway-automated-tests-and-machine-auth-example)

2. Clone the forked repository

```shell
git clone https://github.com/<YOUR_GITHUB_USERNAME>/amazon-api-gateway-automated-tests-and-machine-auth-example
```

3. Edit the cdk.json file

- Change `github_owner` to match your GitHub Username or Organization
- (Optional) Adjust ``

4. Store your GitHub Token in SecretsManager

```shell
aws secretsmanager  create-secret --name github-access-token-secret --description "Github access token" --secret-string {YOUR_GITHUB_TOKEN}
```
You can create your GitHub Token [here](https://github.com/settings/tokens/new). Please select scopes: repo and admin:repohook.

5. Set AWS Account & Region

```shell
export AWS_PROFILE=default
export CDK_DEFAULT_ACCOUNT=123456789123
export CDK_DEPLOY_REGION=eu-central-1
```

6. Install CDK & packages

```shell
# Install CDK 
brew install aws-cdk

# Prepare CDK
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Boostrap CDK
cdk bootstrap
```

7. Deploy CDK

```shell
cdk deploy --all
```


## Test Manually

### Get an Access Token manually

```shell
export API_BASE_URl=https://example.execute-api.eu-central-1.amazonaws.com/prod
export API_CLIENT_ID=	
export API_CLIENT_SECRET_VALUE=
export API_ACCESS_TOKEN_URL=https://example.auth.eu-central-1.amazoncognito.com/oauth2/token

export API_CLIENT_ACCESS_TOKEN=`curl -X POST --user $API_CLIENT_ID:$API_CLIENT_SECRET_VALUE "$API_ACCESS_TOKEN_URL?grant_type=client_credentials" -H 'Content-Type: application/x-www-form-urlencoded' | jq -r '.access_token'`
```

### Call REST API from terminal

```shell
curl -X GET "${API_BASE_URl}/fn/books" -H "Authorization:${API_CLIENT_ACCESS_TOKEN}"
```

### Postman 

- Import the Collection `01 - Performance Testing` into Postman from the file `tests/api/performance_testing/01 - Performance Testing.postman_collection.json`
- Import the Collection `02 - Integration Testing` into Postman from the file `tests/api/02 - Integration Testing.postman_collection.json`

- Add the Access Token to the Colelction Variable `token` after you got it from the CLI. As alternative you can change the authorization to OAuth 2 and let Postman retrieve the token.
- Now you can run tests from Postman UI via "Run" from each collection or folder or single requests via "Send"

### K6
**Not yet implemented**

## Cleanup

```shell
cdk destroy --all
```