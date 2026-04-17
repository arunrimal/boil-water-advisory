resource "google_compute_instance" "app_server" {
  name         = var.vm_name
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
    }
  }

  network_interface {
    network = "default"
    access_config {
      // Ephemeral public IP
    }
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Update system
    apt-get update -y
    apt-get upgrade -y

    # Install Java (Jenkins needs it)
    apt-get install -y openjdk-17-jdk

    # Install Jenkins
    curl -fsSL https://pkg.jenkins.io/debian/jenkins.io-2023.key | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
    echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian binary/ | tee /etc/apt/sources.list.d/jenkins.list > /dev/null
    apt-get update -y
    apt-get install -y jenkins

    # Install Docker
    apt-get install -y docker.io
    systemctl enable docker
    systemctl start docker

    # Add Jenkins user to Docker group
    usermod -aG docker jenkins

    # Start Jenkins
    systemctl enable jenkins
    systemctl start jenkins
  EOF

  tags = ["streamlit", "jenkins"]
}