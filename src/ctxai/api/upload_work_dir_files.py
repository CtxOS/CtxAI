import base64

from ctxai.helpers import runtime
from ctxai.helpers.api import ApiHandler
from ctxai.helpers.file_browser import FileBrowser
from ctxai.helpers.flask_compat import Response, UploadFileAdapter


class UploadWorkDirFiles(ApiHandler):
    async def process(self, input: dict, request) -> dict | Response:
        # Ensure form data is loaded
        await request._ensure_form()

        if "files[]" not in request.files:
            raise Exception("No files uploaded")

        current_path = request.form.get("path", "")
        uploaded_files_raw = request.files.getlist("files[]")

        # Wrap UploadFile objects with FileStorage-compatible adapter
        uploaded_files = []
        for f in uploaded_files_raw:
            adapter = UploadFileAdapter(f)
            await adapter.read_async()
            uploaded_files.append(adapter)

        successful, failed = await upload_files(uploaded_files, current_path)

        if not successful and failed:
            raise Exception("All uploads failed")

        from ctxai.api import get_work_dir_files

        result = await runtime.call_development_function(get_work_dir_files.get_files, current_path)

        return {
            "message": ("Files uploaded successfully" if not failed else "Some files failed to upload"),
            "data": result,
            "successful": successful,
            "failed": failed,
        }


async def upload_files(uploaded_files: list, current_path: str):
    if runtime.is_development():
        successful = []
        failed = []
        for file in uploaded_files:
            file_content = file.stream.read()
            base64_content = base64.b64encode(file_content).decode("utf-8")
            if await runtime.call_development_function(upload_file, current_path, file.filename, base64_content):
                successful.append(file.filename)
            else:
                failed.append(file.filename)
    else:
        browser = FileBrowser()
        successful, failed = browser.save_files(uploaded_files, current_path)

    return successful, failed


async def upload_file(current_path: str, filename: str, base64_content: str):
    browser = FileBrowser()
    return browser.save_file_b64(current_path, filename, base64_content)
