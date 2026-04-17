output "vm_external_ip" {
  description = "External IP address of the VM"
  value       = google_compute_instance.app_server.network_interface[0].access_config[0].nat_ip
}

output "streamlit_url" {
  description = "Streamlit app URL"
  value       = "http://${google_compute_instance.app_server.network_interface[0].access_config[0].nat_ip}:8501"
}

output "jenkins_url" {
  description = "Jenkins URL"
  value       = "http://${google_compute_instance.app_server.network_interface[0].access_config[0].nat_ip}:8080"
}