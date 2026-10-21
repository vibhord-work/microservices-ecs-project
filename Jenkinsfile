pipeline {
    agent any

    options {
        disableConcurrentBuilds()
        timeout(time: 40, unit: 'MINUTES')
        timestamps()
        skipDefaultCheckout(true)
    }

    environment {
        AWS_DEFAULT_REGION = 'us-east-1'
        AWS_PAGER = ''
        PATH = '/usr/local/bin:/usr/bin:/bin'
        BUILD_PROJECT = 'microservices-build'
        ECS_CLUSTER = 'microservices-cluster'
        REGISTRY = '460249938865.dkr.ecr.us-east-1.amazonaws.com'
        ALB_URL = 'http://microservices-alb-952495670.us-east-1.elb.amazonaws.com'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm

                sh '''
                    set -eu
                    git rev-parse HEAD > commit.txt
                    echo "Building commit: $(cat commit.txt)"
                '''
            }
        }

        stage('Build and Test with CodeBuild') {
            steps {
                sh '''
                    set -eu

                    COMMIT=$(cat commit.txt)

                    BUILD_ID=$(aws codebuild start-build \
                      --project-name "$BUILD_PROJECT" \
                      --source-version "$COMMIT" \
                      --query 'build.id' \
                      --output text)

                    echo "CodeBuild started: $BUILD_ID"

                    while true; do
                        aws codebuild batch-get-builds \
                          --ids "$BUILD_ID" > build-result.json

                        STATUS=$(jq -r \
                          '.builds[0].buildStatus // "UNKNOWN"' \
                          build-result.json)

                        echo "CodeBuild status: $STATUS"

                        case "$STATUS" in
                            SUCCEEDED)
                                break
                                ;;
                            IN_PROGRESS)
                                sleep 15
                                ;;
                            *)
                                jq '.builds[0] | {
                                  buildStatus,
                                  phases,
                                  logs
                                }' build-result.json

                                echo "CodeBuild did not succeed."
                                exit 1
                                ;;
                        esac
                    done

                    RESOLVED=$(jq -r \
                      '.builds[0].resolvedSourceVersion' \
                      build-result.json)

                    NUMBER=$(jq -r \
                      '.builds[0].buildNumber' \
                      build-result.json)

                    if [ "$RESOLVED" != "$COMMIT" ]; then
                        echo "CodeBuild built a different commit."
                        exit 1
                    fi

                    SHORT_COMMIT=$(printf '%s' "$RESOLVED" | cut -c1-12)

                    echo "build-${NUMBER}-${SHORT_COMMIT}" > image-tag.txt
                    echo "Images ready: $(cat image-tag.txt)"
                '''
            }
        }

        stage('Deploy to ECS') {
            steps {
                sh '''
                    set -eu

                    IMAGE_TAG=$(cat image-tag.txt)

                    for SERVICE in employee department; do
                        ECS_SERVICE="microservices-${SERVICE}-service"
                        CONTAINER="${SERVICE}-service"
                        IMAGE="${REGISTRY}/microservices-${SERVICE}:${IMAGE_TAG}"

                        CURRENT=$(aws ecs describe-services \
                          --cluster "$ECS_CLUSTER" \
                          --services "$ECS_SERVICE" \
                          --query 'services[0].taskDefinition' \
                          --output text)

                        if [ "$CURRENT" = "None" ] || [ -z "$CURRENT" ]; then
                            echo "Service not found: $ECS_SERVICE"
                            exit 1
                        fi

                        aws ecs describe-task-definition \
                          --task-definition "$CURRENT" \
                          > "${SERVICE}-current.json"

                        jq --arg container "$CONTAINER" --arg image "$IMAGE" '
                          .taskDefinition
                          | del(
                              .taskDefinitionArn,
                              .revision,
                              .status,
                              .requiresAttributes,
                              .compatibilities,
                              .registeredAt,
                              .registeredBy,
                              .deregisteredAt
                            )
                          | if any(.containerDefinitions[];
                              .name == $container)
                            then .containerDefinitions |= map(
                              if .name == $container
                              then .image = $image
                              else .
                              end
                            )
                            else error("Expected container not found")
                            end
                        ' "${SERVICE}-current.json" > "${SERVICE}-new.json"

                        NEW_ARN=$(aws ecs register-task-definition \
                          --cli-input-json "file://${SERVICE}-new.json" \
                          --query 'taskDefinition.taskDefinitionArn' \
                          --output text)

                        echo "$NEW_ARN" > "${SERVICE}-expected.txt"

                        aws ecs update-service \
                          --cluster "$ECS_CLUSTER" \
                          --service "$ECS_SERVICE" \
                          --task-definition "$NEW_ARN" \
                          > /dev/null

                        echo "Deployment started: $ECS_SERVICE"
                        echo "New task definition: $NEW_ARN"
                    done
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                sh '''
                    set -eu

                    for SERVICE in employee department; do
                        ECS_SERVICE="microservices-${SERVICE}-service"
                        EXPECTED=$(cat "${SERVICE}-expected.txt")

                        echo "Waiting for service: $ECS_SERVICE"

                        aws ecs wait services-stable \
                          --cluster "$ECS_CLUSTER" \
                          --services "$ECS_SERVICE"

                        VERIFIED=false

                        for ATTEMPT in $(seq 1 30); do
                            aws ecs describe-services \
                              --cluster "$ECS_CLUSTER" \
                              --services "$ECS_SERVICE" \
                              > "${SERVICE}-result.json"

                            if jq -e --arg expected "$EXPECTED" '
                              .services[0]
                              | (.taskDefinition == $expected)
                                and (.runningCount == .desiredCount)
                                and (.desiredCount > 0)
                                and (.pendingCount == 0)
                                and any(.deployments[];
                                  (.taskDefinition == $expected)
                                  and (.rolloutState == "COMPLETED")
                                )
                            ' "${SERVICE}-result.json" > /dev/null; then
                                VERIFIED=true
                                break
                            fi

                            echo "Waiting for confirmation: $ATTEMPT/30"
                            sleep 10
                        done

                        if [ "$VERIFIED" != "true" ]; then
                            cat "${SERVICE}-result.json"
                            echo "Verification failed: $ECS_SERVICE"
                            exit 1
                        fi

                        echo "Deployment verified: $ECS_SERVICE"
                    done
                '''
            }
        }

        stage('Test Application URLs') {
            steps {
                sh '''
                    set -eu

                    for ENDPOINT in employees departments; do
                        PASSED=false

                        for ATTEMPT in $(seq 1 6); do
                            if curl --fail --silent --show-error \
                              --connect-timeout 10 \
                              --max-time 30 \
                              "$ALB_URL/$ENDPOINT" \
                              -o "${ENDPOINT}-response.json"; then

                                if jq -e --arg endpoint "$ENDPOINT" '
                                  (.[$endpoint] | type == "array")
                                  and (.[$endpoint] | length > 0)
                                ' "${ENDPOINT}-response.json" > /dev/null; then
                                    PASSED=true
                                    break
                                fi
                            fi

                            echo "Retrying $ENDPOINT: $ATTEMPT/6"
                            sleep 10
                        done

                        if [ "$PASSED" != "true" ]; then
                            echo "API verification failed: $ENDPOINT"
                            exit 1
                        fi

                        echo "API verified: $ENDPOINT"
                        cat "${ENDPOINT}-response.json"
                        echo
                    done
                '''
            }
        }
    }

    post {
        success {
            echo 'SUCCESS: Build, tests, ECS deployments, and APIs verified.'
        }

        failure {
            echo 'FAILED: Check the failed stage in Console Output.'
        }
    }
}
