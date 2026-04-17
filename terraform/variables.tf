variable "project_id" {
  description = "Google Cloud Project ID"
  default     = "streamlit-terraform"
}

variable "region" {
  description = "Google Cloud Region"
  default     = "us-central1"
}

variable "zone" {
  description = "Google Cloud Zone"
  default     = "us-central1-a"
}

variable "vm_name" {
  description = "Name of the VM instance"
  default     = "bwa-streamlit-jenkins-vm"
}

variable "machine_type" {
  description = "VM machine type"
  default     = "e2-medium"
}

variable "terraform_state_bucket" {
  description = "Terraform state bucket name"
  default     = "bwa-streamlit-terraform-state"
}

variable "app_data_bucket" {
  description = "Bucket for Streamlit app data"
  default     = "streamlit-app-data"
}