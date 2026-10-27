variable "region" {
  description = "AWS region (Singapore is the closest to Dhaka)"
  type        = string
  default     = "ap-southeast-1"
}

variable "name" {
  type    = string
  default = "extraction-service"
}

variable "kubernetes_version" {
  type    = string
  default = "1.31"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium", "t3a.medium"]
}

variable "admin_cidrs" {
  description = "CIDRs allowed to reach the Kubernetes API endpoint. Set to your IP/32."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "namespace" {
  description = "Namespace the CI role may deploy into"
  type        = string
  default     = "extraction"
}

variable "github_repo" {
  description = "owner/repo allowed to deploy, e.g. wshuv-o/doc-extraction-evals"
  type        = string
  default     = "wshuv-o/doc-extraction-evals"
}

variable "create_github_oidc_provider" {
  description = "false if the account already has the GitHub OIDC provider"
  type        = bool
  default     = true
}
