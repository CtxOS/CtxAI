## Active project
Path: {{project_path}}
Title: {{project_name}}
Description: {{project_description}}
{% if project_git_url %}Git URL: {{project_git_url}}{% endif %}


### Important project instructions MUST follow
- always work inside {{project_path}} directory
- do not rename project directory do not change meta files in .a0proj folder
- Cleanup: if code accidentally creates files outside the project directory, move them into {{project_path}}

{{project_instructions}}
