# FileUploadZone Component

## Overview
A premium, animated, drag-and-drop file upload zone. It uses Framer Motion for smooth state transitions and features internal validation for file extensions and sizes. Designed for dark mode data-pipeline integrations.

## Props
- `onFileSelect` (Function): Callback fired when a valid file is parsed. Passes the native `File` object, or `null` if the user clears the file.
- `accept` (string): Comma-separated list of allowed extensions. Default: `".csv,.parquet,.xlsx"`.
- `maxSizeMB` (number): Max file size constraint. Default: `50`.
- `title` (string): Main bold text.
- `subtitle` (string): Helper text below the title.

## Usage
```jsx
<FileUploadZone 
  title="Upload IFRS9 Portfolio" 
  accept=".parquet"
  maxSizeMB={100}
  onFileSelect={(file) => {
    if(file) console.log("Ready to upload:", file.name);
  }} 
/>
```
