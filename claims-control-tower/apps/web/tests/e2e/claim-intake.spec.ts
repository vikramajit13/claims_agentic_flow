import { expect, test } from "@playwright/test";

test("creates a claim, uploads files, and starts a workflow", async ({ page }) => {
  let claimFetchCount = 0;

  await page.route("http://127.0.0.1:8000/v1/claims", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: 101,
          claim_number: "CLM-2026-001",
          customer_id: 1001,
          claim_type: "motor",
          description: "Rear bumper damage",
          incident_date: "2026-07-28",
          claim_amount: 2400,
          status: "draft",
          documents: [],
          created_at: "2026-07-28T09:00:00+10:00",
          updated_at: "2026-07-28T09:00:00+10:00"
        })
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([])
    });
  });

  await page.route("http://127.0.0.1:8000/v1/claims/101/documents/presign", async (route) => {
    const payload = route.request().postDataJSON() as { file_name: string; content_type?: string | null; run_ocr?: boolean };
    const isImage = payload.file_name.endsWith(".jpg");
    const documentId = isImage ? 201 : 202;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        document_id: documentId,
        upload_url: `https://mock-s3.local/upload/${documentId}`,
        upload_method: "PUT",
        upload_headers: {
          "x-amz-meta-document-id": String(documentId)
        },
        s3_uri: `s3://claims-bucket/claims/101/${payload.file_name}`,
        s3_bucket: "claims-bucket",
        s3_key: `claims/101/${payload.file_name}`,
        expires_in_seconds: 900
      })
    });
  });

  await page.route("https://mock-s3.local/**", async (route) => {
    await route.fulfill({ status: 200, body: "" });
  });

  await page.route("http://127.0.0.1:8000/v1/claims/101/documents/*/complete-upload", async (route) => {
    const documentId = Number(route.request().url().split("/").slice(-2)[0]);
    const isImage = documentId === 201;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: documentId,
        file_name: isImage ? "damage-photo.jpg" : "repair-invoice.pdf",
        content_type: isImage ? "image/jpeg" : "application/pdf",
        s3_uri: `s3://claims-bucket/claims/101/${isImage ? "damage-photo.jpg" : "repair-invoice.pdf"}`,
        s3_bucket: "claims-bucket",
        s3_key: `claims/101/${isImage ? "damage-photo.jpg" : "repair-invoice.pdf"}`,
        upload_status: isImage ? "uploaded" : "ocr_completed",
        ocr_requested: !isImage,
        ocr_status: isImage ? "not_requested" : "completed",
        ocr_job_id: null,
        ocr_error: null,
        ocr_text: isImage ? null : "Mock OCR extracted text",
        normalized_text: isImage ? null : "Mock OCR extracted text",
        validation_results: null,
        document_classification: { document_type: isImage ? "photo" : "invoice" },
        extracted_fields: isImage
          ? null
          : {
              invoice_amount: 2400,
              invoice_date: "2026-07-28",
              vendor_name: "Sydney Repairs"
            },
        quality_assessment: { review_recommended: false },
        normalized_payload: {
          document_type: isImage ? "photo" : "invoice",
          extracted_fields: isImage
            ? {}
            : {
                invoice_amount: 2400,
                invoice_date: "2026-07-28",
                vendor_name: "Sydney Repairs"
              }
        },
        normalized_document_type: isImage ? "photo" : "invoice",
        normalized_confidence: 0.97,
        normalized_at: "2026-07-28T09:01:00+10:00",
        created_at: "2026-07-28T09:00:00+10:00",
        updated_at: "2026-07-28T09:01:00+10:00"
      })
    });
  });

  await page.route("http://127.0.0.1:8000/v1/claims/101", async (route) => {
    claimFetchCount += 1;

    const documents =
      claimFetchCount === 1
        ? [
            {
              id: 201,
              file_name: "damage-photo.jpg",
              content_type: "image/jpeg",
              s3_uri: "s3://claims-bucket/claims/101/damage-photo.jpg",
              s3_bucket: "claims-bucket",
              s3_key: "claims/101/damage-photo.jpg",
              upload_status: "uploaded",
              ocr_requested: false,
              ocr_status: "not_requested",
              ocr_job_id: null,
              ocr_error: null,
              ocr_text: null,
              normalized_text: null,
              validation_results: null,
              document_classification: { document_type: "photo" },
              extracted_fields: null,
              quality_assessment: { review_recommended: false },
              normalized_payload: { document_type: "photo", extracted_fields: {} },
              normalized_document_type: "photo",
              normalized_confidence: 0.98,
              normalized_at: "2026-07-28T09:01:00+10:00",
              created_at: "2026-07-28T09:00:00+10:00",
              updated_at: "2026-07-28T09:01:00+10:00"
            }
          ]
        : [
            {
              id: 201,
              file_name: "damage-photo.jpg",
              content_type: "image/jpeg",
              s3_uri: "s3://claims-bucket/claims/101/damage-photo.jpg",
              s3_bucket: "claims-bucket",
              s3_key: "claims/101/damage-photo.jpg",
              upload_status: "uploaded",
              ocr_requested: false,
              ocr_status: "not_requested",
              ocr_job_id: null,
              ocr_error: null,
              ocr_text: null,
              normalized_text: null,
              validation_results: null,
              document_classification: { document_type: "photo" },
              extracted_fields: null,
              quality_assessment: { review_recommended: false },
              normalized_payload: { document_type: "photo", extracted_fields: {} },
              normalized_document_type: "photo",
              normalized_confidence: 0.98,
              normalized_at: "2026-07-28T09:01:00+10:00",
              created_at: "2026-07-28T09:00:00+10:00",
              updated_at: "2026-07-28T09:01:00+10:00"
            },
            {
              id: 202,
              file_name: "repair-invoice.pdf",
              content_type: "application/pdf",
              s3_uri: "s3://claims-bucket/claims/101/repair-invoice.pdf",
              s3_bucket: "claims-bucket",
              s3_key: "claims/101/repair-invoice.pdf",
              upload_status: "ocr_completed",
              ocr_requested: true,
              ocr_status: "completed",
              ocr_job_id: null,
              ocr_error: null,
              ocr_text: "Mock OCR extracted text",
              normalized_text: "Mock OCR extracted text",
              validation_results: null,
              document_classification: { document_type: "invoice" },
              extracted_fields: {
                invoice_amount: 2400,
                invoice_date: "2026-07-28",
                vendor_name: "Sydney Repairs"
              },
              quality_assessment: { review_recommended: false },
              normalized_payload: {
                document_type: "invoice",
                extracted_fields: {
                  invoice_amount: 2400,
                  invoice_date: "2026-07-28",
                  vendor_name: "Sydney Repairs"
                }
              },
              normalized_document_type: "invoice",
              normalized_confidence: 0.97,
              normalized_at: "2026-07-28T09:02:00+10:00",
              created_at: "2026-07-28T09:00:00+10:00",
              updated_at: "2026-07-28T09:02:00+10:00"
            }
          ];

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 101,
        claim_number: "CLM-2026-001",
        customer_id: 1001,
        claim_type: "motor",
        description: "Rear bumper damage",
        incident_date: "2026-07-28",
        claim_amount: 2400,
        status: "submitted",
        documents,
        created_at: "2026-07-28T09:00:00+10:00",
        updated_at: "2026-07-28T09:02:00+10:00"
      })
    });
  });

  await page.route("http://127.0.0.1:8000/v1/workflows/claims/101/start", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: 301,
        claim_id: 101,
        status: "ready_for_graph",
        current_step: "graph_bootstrap",
        hitl_required: false,
        next_action: "Claim is ready for graph orchestration.",
        notes: ["Started from web intake console"],
        created_at: "2026-07-28T09:03:00+10:00",
        updated_at: "2026-07-28T09:03:00+10:00"
      })
    });
  });

  await page.goto("/");

  await page.getByLabel("Claim number").fill("CLM-2026-001");
  await page.getByLabel("Customer id").fill("1001");
  await page.getByLabel("Description").fill("Rear bumper damage");
  await page.getByLabel("Incident date").fill("2026-07-28");
  await page.getByLabel("Claim amount").fill("2400");
  await page.getByRole("button", { name: "Create claim" }).click();

  await expect(page.getByText("Claim CLM-2026-001 created with id 101.")).toBeVisible();
  await expect(page.getByText("CLM-2026-001").first()).toBeVisible();

  await page.getByTestId("document-input").setInputFiles([
    {
      name: "damage-photo.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.from("fake-image")
    },
    {
      name: "repair-invoice.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("fake-pdf")
    }
  ]);

  await page.getByTestId("upload-all-button").click();

  await expect(page.getByText("Upload completed for damage-photo.jpg. OCR status: not_requested.")).toBeVisible();
  await expect(page.getByText("Upload completed for repair-invoice.pdf. OCR status: completed.")).toBeVisible();

  await page.getByTestId("start-workflow-button").click();

  await expect(page.getByText("Workflow 301 started in step graph_bootstrap.")).toBeVisible();
  await expect(page.getByText("Claim is ready for graph orchestration.")).toBeVisible();
});
