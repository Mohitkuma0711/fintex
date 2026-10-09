import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { AnimatePresence, motion } from 'framer-motion'
import {
  AlertTriangle,
  ArrowRight,
  Check,
  FileImage,
  FileText,
  LoaderCircle,
  LockKeyhole,
  RotateCcw,
  ScanLine,
  ShieldCheck,
  Upload,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { fintaxApi, type DocumentExtractionResponse } from '../lib/api'

const allowedFiles = {
  'application/pdf': ['.pdf'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
}

const extractionSteps = [
  { id: 'upload', label: 'Secure upload received' },
  { id: 'scan', label: 'File and safety checks' },
  { id: 'extract', label: 'AI is reading your document' },
  { id: 'review', label: 'Preparing your review' },
]

function stepState(
  stepId: string,
  extraction: DocumentExtractionResponse,
  uploading: boolean,
): 'complete' | 'active' | 'waiting' | 'warning' {
  if (stepId === 'upload') return uploading ? 'active' : 'complete'
  if (extraction.status === 'failed') return stepId === 'extract' ? 'warning' : 'complete'
  if (stepId === 'scan') {
    if (extraction.scan_status === 'clean') return 'complete'
    return extraction.status === 'processing' ? 'warning' : 'waiting'
  }
  if (stepId === 'extract') {
    if (extraction.status === 'extracted') return 'complete'
    return extraction.status === 'processing' ? 'active' : 'waiting'
  }
  return extraction.status === 'extracted' ? 'complete' : 'waiting'
}

function fileLabel(contentType: string) {
  return contentType === 'application/pdf' ? 'PDF document' : 'Image document'
}

export function UploadPage() {
  const [documentType, setDocumentType] = useState<'form16' | 'salary_slip'>('form16')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [dropError, setDropError] = useState('')
  const [autoDeleteAfter30Days, setAutoDeleteAfter30Days] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const upload = useMutation({
    mutationFn: (file: File) =>
      fintaxApi.uploadDocument(file, documentType, setUploadProgress, autoDeleteAfter30Days),
    onSuccess: async (result) => {
      setDocumentId(result.id)
      setUploadProgress(100)
      await queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: (error: Error) => {
      setDropError(error.message)
    },
  })

  const extraction = useQuery({
    queryKey: ['document-extraction', documentId],
    queryFn: () => fintaxApi.getDocumentExtraction(documentId!),
    enabled: documentId !== null,
    refetchInterval: (query) => {
      const current = query.state.data?.status
      return current === 'pending' || current === 'processing' ? 1200 : false
    },
    refetchOnWindowFocus: true,
  })

  const retry = useMutation({
    mutationFn: (id: string) => fintaxApi.retryDocumentExtraction(id),
    onSuccess: (result) => {
      queryClient.setQueryData(['document-extraction', result.id], result)
      setDropError('')
    },
    onError: (error: Error) => setDropError(error.message),
  })

  useEffect(() => {
    if (extraction.data?.status === 'extracted' && documentId) {
      const extractionId = extraction.data.extraction_id
      const search = new URLSearchParams({ documentId })
      if (extractionId) search.set('extractionId', extractionId)
      navigate(`/review?${search.toString()}`)
    }
  }, [documentId, extraction.data?.extraction_id, extraction.data?.status, navigate])

  const dropzone = useDropzone({
    accept: allowedFiles,
    maxSize: 50 * 1024 * 1024,
    maxFiles: 1,
    disabled: upload.isPending || documentId !== null,
    onDrop: (acceptedFiles, rejectedFiles) => {
      setDropError('')
      if (rejectedFiles.length > 0) {
        const code = rejectedFiles[0]?.errors[0]?.code
        setDropError(
          code === 'file-too-large'
            ? 'This file exceeds the 50 MiB maximum.'
            : 'Choose a PDF, JPG, or PNG document.',
        )
        return
      }
      setSelectedFile(acceptedFiles[0] ?? null)
    },
  })

  function startUpload() {
    if (!selectedFile || upload.isPending) return
    setDropError('')
    setUploadProgress(0)
    upload.mutate(selectedFile)
  }

  function retryUpload() {
    setDocumentId(null)
    setUploadProgress(0)
    setDropError('')
    upload.reset()
    if (selectedFile) upload.mutate(selectedFile)
  }

  const currentExtraction = extraction.data
  const pageError = dropError || extraction.error?.message || ''
  const extractionFailed = currentExtraction?.status === 'failed'
  const isProcessing =
    upload.isPending ||
    currentExtraction?.status === 'pending' ||
    currentExtraction?.status === 'processing'

  return (
    <section className="upload-page container">
      <div className="upload-page__topline">
        <Link className="text-link" to="/dashboard">← Back to workspace</Link>
        <span><LockKeyhole aria-hidden="true" size={14} /> Private document workspace</span>
      </div>

      <div className="upload-heading">
        <p className="eyebrow">STEP 01 · UPLOAD</p>
        <h1>Your documents, <span>your pace.</span></h1>
        <p>Start with a Form 16 or salary slip. We’ll extract what is visible, then let you review it.</p>
      </div>

      {!documentId && (
        <div className="upload-layout">
          <div>
            <div className="upload-type-control">
              <label htmlFor="document-type">Document type</label>
              <select
                id="document-type"
                onChange={(event) =>
                  setDocumentType(event.target.value as 'form16' | 'salary_slip')
                }
                value={documentType}
              >
                <option value="form16">Form 16</option>
                <option value="salary_slip">Salary slip</option>
              </select>
            </div>
            <button
              {...dropzone.getRootProps({
                className: `upload-dropzone${dropzone.isDragActive ? ' upload-dropzone--active' : ''}`,
              })}
              type="button"
            >
              <input {...dropzone.getInputProps()} />
              <span className="upload-dropzone__icon">
                <Upload aria-hidden="true" size={24} />
              </span>
              <strong>{dropzone.isDragActive ? 'Drop your file to begin' : 'Drop your document here'}</strong>
              <span>or <span className="upload-dropzone__browse">browse files</span></span>
              <small>PDF, JPG, or PNG · Up to 50 MiB</small>
            </button>
            <label className="upload-retention-option">
              <input
                checked={autoDeleteAfter30Days}
                onChange={(event) => setAutoDeleteAfter30Days(event.currentTarget.checked)}
                type="checkbox"
              />
              <span>Automatically delete this uploaded file after 30 days</span>
            </label>
            {selectedFile && (
              <div className="upload-selected-file">
                {selectedFile.type === 'application/pdf'
                  ? <FileText aria-hidden="true" size={19} />
                  : <FileImage aria-hidden="true" size={19} />}
                <span>
                  <strong>{selectedFile.name}</strong>
                  <small>{fileLabel(selectedFile.type)} · {(selectedFile.size / 1024 / 1024).toFixed(2)} MiB</small>
                </span>
                <button
                  aria-label="Remove selected file"
                  className="upload-remove-file"
                  onClick={() => setSelectedFile(null)}
                  type="button"
                >
                  Remove
                </button>
              </div>
            )}
            {upload.isPending && (
              <div aria-live="polite" className="upload-progress">
                <div className="upload-progress__label">
                  <span>Uploading securely</span><span>{uploadProgress}%</span>
                </div>
                <div
                  aria-label={`Upload progress ${uploadProgress}%`}
                  aria-valuemax={100}
                  aria-valuemin={0}
                  aria-valuenow={uploadProgress}
                  className="upload-progress__track"
                  role="progressbar"
                >
                  <span style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}
            {pageError && <p className="upload-error" role="alert">{pageError}</p>}
            {selectedFile && !upload.isPending && (
              <button className="button button--primary upload-submit" onClick={startUpload} type="button">
                Upload and extract <ArrowRight aria-hidden="true" size={17} />
              </button>
            )}
            {upload.isError && selectedFile && (
              <button className="button upload-retry-upload" onClick={retryUpload} type="button">
                <RotateCcw aria-hidden="true" size={15} /> Retry upload
              </button>
            )}
          </div>
          <aside className="upload-privacy-card">
            <span><ShieldCheck aria-hidden="true" size={19} /></span>
            <h2>Private by design</h2>
            <p>Your file is stored in a private, user-scoped bucket. Access links expire automatically.</p>
            <p className="upload-privacy-card__note">
              Files are checked against their actual file signature. Virus scanning is not enabled in this environment.
            </p>
          </aside>
        </div>
      )}

      {documentId && (
        <div aria-live="polite" className={`extraction-panel${isProcessing ? ' extraction-panel--active' : ''}`}>
          <div className="extraction-panel__visual">
            <motion.div
              animate={isProcessing ? { scale: [1, 1.04, 1], opacity: [0.75, 1, 0.75] } : { scale: 1, opacity: 1 }}
              className="extraction-orb"
              transition={isProcessing ? { duration: 2, repeat: Infinity, ease: 'easeInOut' } : { duration: 0.3 }}
            >
              {extractionFailed
                ? <AlertTriangle aria-hidden="true" size={32} />
                : currentExtraction?.status === 'extracted'
                  ? <Check aria-hidden="true" size={32} />
                  : <ScanLine aria-hidden="true" size={32} />}
              {isProcessing && <span className="extraction-orb__scan" />}
            </motion.div>
            <div>
              <p className="eyebrow">{extractionFailed ? 'NEEDS ATTENTION' : 'SECURE EXTRACTION'}</p>
              <h2>{extractionFailed ? 'We couldn’t finish reading this file.' : 'AI is reading your document.'}</h2>
              <p>
                {extractionFailed
                  ? 'Your original file remains private. Retry extraction or upload a clearer copy.'
                  : 'We’re identifying only the details visible in your document. You’ll review each result next.'}
              </p>
            </div>
          </div>
          <ol className="extraction-steps">
            {extractionSteps.map((step) => {
              const state = currentExtraction
                ? stepState(step.id, currentExtraction, upload.isPending)
                : upload.isPending
                  ? step.id === 'upload' ? 'active' : 'waiting'
                  : 'complete'
              return (
                <li className={`extraction-step extraction-step--${state}`} key={step.id}>
                  <span className="extraction-step__icon">
                    {state === 'complete'
                      ? <Check aria-hidden="true" size={15} />
                      : state === 'active'
                        ? <LoaderCircle aria-hidden="true" className="extraction-spinner" size={15} />
                        : state === 'warning'
                          ? <AlertTriangle aria-hidden="true" size={15} />
                          : <span />}
                  </span>
                  <span>{step.label}</span>
                  {step.id === 'scan' && currentExtraction?.scan_status === 'not_scanned' && (
                    <small>Virus scan unavailable</small>
                  )}
                </li>
              )
            })}
          </ol>
          {currentExtraction?.status === 'processing' && currentExtraction.scan_status === 'not_scanned' && (
            <p className="extraction-warning">
              <AlertTriangle aria-hidden="true" size={16} />
              Virus scanning is not configured. The file signature is checked, but this is not a malware scan.
            </p>
          )}
          {extraction.isError && (
            <div className="extraction-error">
              <p className="upload-error" role="alert">{extraction.error.message}</p>
              <button className="button upload-retry-upload" onClick={() => void extraction.refetch()} type="button">
                <RotateCcw aria-hidden="true" size={15} /> Retry status check
              </button>
            </div>
          )}
          {extractionFailed && (
            <div className="extraction-error">
              <p className="upload-error" role="alert">
                {currentExtraction.error_code ?? 'extraction_failed'}
              </p>
              <button
                className="button button--primary upload-submit"
                disabled={retry.isPending}
                onClick={() => retry.mutate(documentId)}
                type="button"
              >
                <RotateCcw aria-hidden="true" size={15} /> Retry extraction
              </button>
              {retry.isError && <p className="upload-error" role="alert">{retry.error.message}</p>}
            </div>
          )}
          <AnimatePresence>
            {currentExtraction?.status === 'extracted' && (
              <motion.div
                animate={{ opacity: 1, y: 0 }}
                className="extraction-complete"
                exit={{ opacity: 0, y: -8 }}
                initial={{ opacity: 0, y: 8 }}
              >
                <span><Check aria-hidden="true" size={16} /> Extraction complete — opening review…</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </section>
  )
}
