import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, CheckCircle, AlertCircle } from 'lucide-react';
import { documentApi } from '../services/api';
import { DocumentUploadResponse } from '../types';
import toast from 'react-hot-toast';

interface DocumentUploadProps {
  onUploadSuccess?: (response: DocumentUploadResponse) => void;
  onUploadError?: (error: string) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
  onUploadError,
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ [key: string]: number }>({});

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true);
    
    for (const file of acceptedFiles) {
      try {
        setUploadProgress(prev => ({ ...prev, [file.name]: 0 }));
        
        const response = await documentApi.upload(file);
        
        setUploadProgress(prev => ({ ...prev, [file.name]: 100 }));
        
        toast.success(`${file.name} uploaded successfully!`);
        
        if (onUploadSuccess) {
          onUploadSuccess(response);
        }
        
        // Reset progress after a delay
        setTimeout(() => {
          setUploadProgress(prev => {
            const newProgress = { ...prev };
            delete newProgress[file.name];
            return newProgress;
          });
        }, 2000);
        
      } catch (error: any) {
        setUploadProgress(prev => ({ ...prev, [file.name]: -1 }));
        
        const errorMessage = error.detail || 'Upload failed';
        toast.error(`${file.name}: ${errorMessage}`);
        
        if (onUploadError) {
          onUploadError(errorMessage);
        }
      }
    }
    
    setUploading(false);
  }, [onUploadSuccess, onUploadError]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true,
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${isDragActive 
            ? 'border-primary-500 bg-primary-50' 
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
          }
        `}
      >
        <input {...getInputProps()} />
        
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        
        {isDragActive ? (
          <p className="text-primary-600 font-medium">Drop the files here...</p>
        ) : (
          <div>
            <p className="text-gray-600 mb-2">
              Drag & drop files here, or <span className="text-primary-600 font-medium">click to select</span>
            </p>
            <p className="text-sm text-gray-500">
              Supports PDF, TXT, DOCX files up to 10MB
            </p>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="mt-6 space-y-3">
          <h3 className="text-lg font-medium text-gray-900">Upload Progress</h3>
          
          {Object.entries(uploadProgress).map(([fileName, progress]) => (
            <div key={fileName} className="bg-white border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <FileText className="h-5 w-5 text-gray-400" />
                  <span className="text-sm font-medium text-gray-900">{fileName}</span>
                </div>
                
                {progress === 100 && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                
                {progress === -1 && (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                )}
                
                {progress >= 0 && progress < 100 && (
                  <span className="text-sm text-gray-500">{progress}%</span>
                )}
              </div>
              
              {progress >= 0 && progress < 100 && (
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Selected Files */}
      {acceptedFiles.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Selected Files</h3>
          <div className="space-y-2">
            {acceptedFiles.map((file) => (
              <div key={file.name} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                <div className="flex items-center space-x-3">
                  <FileText className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Button */}
      {acceptedFiles.length > 0 && !uploading && (
        <div className="mt-6">
          <button
            onClick={() => onDrop(acceptedFiles as File[])}
            className="w-full bg-primary-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors"
          >
            Upload {acceptedFiles.length} file{acceptedFiles.length > 1 ? 's' : ''}
          </button>
        </div>
      )}

      {/* Loading State */}
      {uploading && (
        <div className="mt-6 text-center">
          <div className="inline-flex items-center space-x-2">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
            <span className="text-gray-600">Uploading files...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;