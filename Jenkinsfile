pipeline {
    agent any

    environment {
        GCP_VM_IP = '34.132.110.25'
        VM_USER = 'aarunrimal'
        IMAGE_NAME = 'bwa-streamlit-app'
        CONTAINER_NAME = 'bwa-streamlit-container'
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Pulling code from GitHub...'
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                withCredentials([file(credentialsId: 'gcp-credentials', variable: 'GCP_CREDS')]) {
                    sh '''
                        rm -f app/credentials.json || true
                        cp $GCP_CREDS app/credentials.json
                        cd app
                        docker build -t ${IMAGE_NAME} .
                    '''
                }
            }
        }

        stage('Stop Old Container') {
            steps {
                echo 'Stopping old container...'
                sh '''
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                '''
            }
        }

        stage('Run New Container') {
            steps {
                echo 'Starting new container...'
                sh '''
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        -p 8501:8501 \
                        ${IMAGE_NAME}
                '''
            }
        }
    }

    post {
        success {
            echo '✅ Deployment successful! App is live at http://${GCP_VM_IP}:8501'
        }
        failure {
            echo '❌ Deployment failed!'
        }
    }
}