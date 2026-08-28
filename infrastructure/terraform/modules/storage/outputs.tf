output "resumes_bucket_name" {
  value = google_storage_bucket.resumes_bucket.name
}

output "documents_bucket_name" {
  value = google_storage_bucket.documents_bucket.name
}

output "pdf_exports_bucket_name" {
  value = google_storage_bucket.pdf_exports_bucket.name
}
