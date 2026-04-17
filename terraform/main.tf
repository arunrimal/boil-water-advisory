terraform {
  required_providers {
    google = {  
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "bwa-streamlit-terraform-state"
    prefix = "terraform/state"
    credentials = "credentials.json"  # ← add this line!
  }
}

provider "google" {
  credentials = file("credentials.json")
  project     = "streamlit-terraform"
  region      = "us-central1"
  zone        = "us-central1-a"
}