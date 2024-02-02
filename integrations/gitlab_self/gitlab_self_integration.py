import anchorpoint as ap
import apsync as aps
from gitlab_self_client import *
from urllib.parse import urlparse, urlunparse
import os

integration_tags = ["git", "self_gitlab"]
connect_action_id = "self_gitlab_connect"
disconnect_action_id = "self_gitlab_disconnect"
reconnect_action_id = "self_gitlab_reconnect"
setup_action_id = "self_gitlab_setup"
settings_action_id = "self_gitlab_settings"
clear_action_id = "self_gitlab_clear"
settings_group_dropdown_entry = "group_dropdown"
settings_credential_btn_entry = "credential_btn"
settings_credential_btn_highlight_entry = "credential_btn_highlight"
create_repo_dialog_entry = "self_gitlab_create_repo"
repo_dropdown_entry = "self_gitlab_repository_dropdown"
create_dialog_info_entry = "self_gitlab_create_dialog_info"
integration_project_name_key = "project_name"

server_url_entry = "server_url"
client_id_entry = "client_id"
client_values_info_entry = "client_values_info"
connect_to_server_btn_entry = "connect_to_server_btn"
remove_data_entry = "remove_data"


def on_load_integrations(integrations, ctx: ap.Context):
    integration = GitlabSelfIntegration(ctx)
    integrations.add(integration)

def on_add_user_to_workspace(email, ctx: ap.Context):
    client = GitlabSelfClient(ctx.workspace_id)

    if not client.is_setup():
        return
    
    client.setup_workspace_settings()
    current_group = client.get_current_group()
    if current_group is None:
        ap.UI().show_error(title='Cannot add member to Gitlab', duration=6000, description=f'Failed to get current group. You have to add your member directly on GitLab.')
        return
    
    if current_group.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot add member to Gitlab', duration=6000, description=f'Failed to connect integration. You have to add your member directly on GitLab.')
        return
    
    try:
        client.add_user_to_group(current_group, email)
        ap.UI().show_success(title='Member added to Gitlab', duration=3000, description=f'User {email} added to group {current_group.name}.')
    except Exception as e:
        print(str(e))
        ap.UI().show_error(title='Cannot add member to Gitlab', duration=10000, description=f'Cannot to add the member to the group. You have to add your member <a href="{client.get_host_url()}/groups/{current_group.path}/-/group_members">directly on your GitLab server</a>.')

def on_remove_user_from_workspace(email, ctx: ap.Context):
    client = GitlabSelfClient(ctx.workspace_id)

    if not client.is_setup():
        return
    
    client.setup_workspace_settings()
    current_group = client.get_current_group()
    if current_group is None:
        ap.UI().show_error(title='Cannot remove member to Gitlab', duration=6000, description=f'Cannot get current group. You have to remove your member directly on GitLab.')
        return
    
    if current_group.is_user:
        return

    if not client.init():
        ap.UI().show_error(title='Cannot remove member to Gitlab', duration=6000, description=f'Failed to connect integration. You have to remove your member directly on GitLab.')
        return
    
    try:
        client.remove_user_from_group(current_group, email)
        ap.UI().show_success(title='Member removed from Gitlab', duration=3000, description=f'User {email} removed from group {current_group.name}.')
    except Exception as e:
        print(str(e))
        ap.UI().show_error(title='Cannot remove member from Gitlab', duration=10000, description=f'Cannot remove member from group. You have to remove your member <a href="{client.get_host_url()}/groups/{current_group.path}/-/group_members">directly from your GitLab server</a>.')

def on_add_user_to_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitlabSelfClient(ctx.workspace_id)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=6000, description=f'Gitlab integration is not setup. Please add manually.')
        return
    
    client.setup_workspace_settings()
    
    if not client.init():
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_group = client.get_current_group()

    try:
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.add_user_to_project(current_group, email, project_name)
        ap.UI().show_success(title='Member added to Gitlab project', duration=3000, description=f'User {email} added to project {project.name}.')
    except Exception as e:
        repo_name = client.generate_gitlab_repo_name(project.name)
        print(str(e))
        ap.UI().show_error(title='Cannot add member to Gitlab project', duration=10000, description=f'You have to add your member <a href="{client.get_host_url()}/{current_group.path}/{repo_name}/-/project_members">directly on your GitLab server</a>.')
        return
    
def on_remove_user_from_project(email, ctx: ap.Context):
    settings = aps.SharedSettings(ctx.project_id, ctx.workspace_id, "integration_info")
    project_integration_tags = settings.get("integration_tags")
    supports_all_tags = all(tag in project_integration_tags.split(';') for tag in integration_tags)

    if not supports_all_tags:
        return
    
    project = aps.get_project_by_id(ctx.project_id, ctx.workspace_id)
    if project is None:
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=6000, description=f'Failed to find project with id {ctx.projectId}. Please add manually.')
        return
    
    client = GitlabSelfClient(ctx.workspace_id)
    
    if not client.is_setup():
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=6000, description=f'Gitlab integration is not setup. Please add manually.')
        return
    
    client.setup_workspace_settings()
    
    if not client.init():
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=6000, description=f'Failed to connect integration. Please add manually.')
        return
    
    current_group = client.get_current_group()

    try:
        project_name = project.name
        integration_project_name = settings.get(integration_project_name_key, None)
        if integration_project_name is not None:
            project_name = integration_project_name
        client.remove_user_from_project(current_group, email, project_name)
        ap.UI().show_success(title='Member removed from Gitlab project', duration=3000, description=f'User {email} removed from project {project.name}.')
    except Exception as e:
        repo_name = client.generate_gitlab_repo_name(project.name)
        ap.UI().show_error(title='Cannot remove member from Gitlab project', duration=10000, description=f'Failed to remove member, because "{str(e)}". You have to remove your member <a href="{client.get_host_url()}/{current_group.path}/{repo_name}/-/project_members">directly from your GitLab server</a>.')
        return

def setup_credentials_async(dialog, host_url: str):
    import sys, os
    script_dir = os.path.join(os.path.dirname(__file__), "..", "..", "versioncontrol")
    sys.path.insert(0, script_dir)
    from vc.apgit.repository import GitRepository
    try:
        dialog.set_processing(settings_credential_btn_highlight_entry, True, "Updating")
        dialog.set_processing(settings_credential_btn_entry, True, "Updating")

        parsed_url = urlparse(host_url)
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
        path = parsed_url.path if parsed_url.path != '' else None

        GitRepository.erase_credentials(netloc, scheme, path)
        result = GitRepository.get_credentials(netloc, scheme, path)
        if (result is None or result.get("host") is None or result["host"] != netloc 
            or result.get("username") is None or result.get("password") is None):
            raise Exception("Login failed")
        GitRepository.store_credentials(netloc, scheme, result["username"], result["password"], path)
        ap.UI().show_success(title='Gitlab credentials stored', duration=3000, description=f'Gitlab credentials stored successfully.')
    except Exception as e:
        ap.UI().show_error(title='Cannot store Gitlab credentials', duration=6000, description=f'Failed to store credentials, because "{str(e)}". Please try again.')
    finally:
        dialog.set_processing(settings_credential_btn_highlight_entry, False)
        dialog.set_processing(settings_credential_btn_entry, False)
        if script_dir in sys.path:
            sys.path.remove(script_dir)

class GitlabSelfIntegration(ap.ApIntegration):
    def __init__(self, ctx: ap.Context):
        super().__init__()
        self.ctx = ctx
        config = ap.get_config()
        self.client = GitlabSelfClient(ctx.workspace_id)

        self.name = 'Gitlab (Self-Hosted)'
        self.description = "Manage your own hosted Gitlab server directly from Anchorpoint.<br>Each member will need an Gitlab (Self-Hosted) account. <a href='https://docs.anchorpoint.app/docs/1-overview/integrations/gitlab_self/'>Learn more</a>"
        self.priority = 97
        self.tags = integration_tags

        icon_path = os.path.join(ctx.yaml_dir, "gitlab_self/logo.svg")
        self.dashboard_icon = icon_path
        self.preferences_icon = icon_path
        self.is_setup = self.client.is_setup()
        self.is_setup_for_workspace = self.client.is_setup_for_workspace()

        if self.is_setup:
            self.client.setup_workspace_settings()
            if self.client.setup_refresh_token():
                self._setup_connected_state()
            else:
                self._setup_reconnect_state()
        else:
            self._setup_not_connected_state()

        createRepo = ap.IntegrationAction()
        createRepo.name = "New Gitlab (Self-Hosted) Repository"
        createRepo.identifier = create_repo_dialog_entry
        createRepo.enabled = True
        createRepo.icon = aps.Icon(":/icons/organizations-and-products/gitlab.svg")
        self.add_create_project_action(createRepo)

    def _setup_not_connected_state(self):
        self.clear_preferences_actions()

        connect = ap.IntegrationAction()
        connect.name = "Connect"
        connect.enabled = True
        connect.icon = aps.Icon(":/icons/plug.svg")
        connect.identifier = connect_action_id
        connect.tooltip = "Connect to Gitlab"
        self.add_preferences_action(connect)

        if(self.is_setup_for_workspace):
            disconnect = ap.IntegrationAction()
            disconnect.name = "Clear"
            disconnect.enabled = True
            disconnect.icon = aps.Icon(":/icons/clearCache.svg")
            disconnect.identifier = disconnect_action_id
            disconnect.tooltip = "Clear Gitlab (Self-Hosted) configuration"
            self.add_preferences_action(disconnect)
        self.is_connected = False

    def _setup_connected_state(self):
        self.clear_preferences_actions()

        disconnect = ap.IntegrationAction()
        disconnect.name = "Disconnect"
        disconnect.enabled = True
        disconnect.icon = aps.Icon(":/icons/unPlug.svg")
        disconnect.identifier = disconnect_action_id
        disconnect.tooltip = "Clear Gitlab (Self-Hosted) configuration"
        self.add_preferences_action(disconnect)

        settings = ap.IntegrationAction()
        settings.name = "Settings"
        settings.enabled = True
        settings.icon = aps.Icon(":/icons/wheel.svg")
        settings.identifier = settings_action_id
        settings.tooltip = "Open settings for Gitlab (Self-Hosted) integration"
        self.add_preferences_action(settings)

        self.is_connected = True

    def _setup_reconnect_state(self):
        self.clear_preferences_actions()

        reconnect = ap.IntegrationAction()
        reconnect.name = "Reconnect"
        reconnect.enabled = True
        reconnect.icon = aps.Icon(":/icons/plug.svg")
        reconnect.identifier = reconnect_action_id
        reconnect.tooltip = "Reconnect to Gitlab (Self-Hosted)"
        self.add_preferences_action(reconnect)

        if(self.is_setup_for_workspace):
            disconnect = ap.IntegrationAction()
            disconnect.name = "Clear"
            disconnect.enabled = True
            disconnect.icon = aps.Icon(":/icons/clearCache.svg")
            disconnect.identifier = disconnect_action_id
            disconnect.tooltip = "Clear Gitlab (Self-Hosted) configuration"
            self.add_preferences_action(disconnect)

        self.is_connected = False
    
    def execute_preferences_action(self, action_id: str):
        if action_id == connect_action_id:
            if not self.client.is_setup_for_workspace():
                self.show_workspace_setup_dialog()
            else:
                self.client.setup_workspace_settings()
                self.client.start_auth()
                self.start_auth()
        elif action_id == disconnect_action_id:
            self.show_clear_integration_dialog()
        elif action_id == reconnect_action_id:
            if not self.client.is_setup_for_workspace():
                self.show_workspace_setup_dialog()
            else:
                self.client.setup_workspace_settings()
                self.client.start_auth()
                self.start_auth()
        elif action_id == settings_action_id:
            try:
                groups = self.client.get_groups()
                if not groups:
                    raise Exception("Failed to load groups")
                current_group = self.client.get_current_group()
                if current_group is None:
                    current_group = groups[0]
                    self.client.set_current_group(current_group)
                self.show_settings_dialog(current_group, groups)
            except Exception as e:
                ap.UI().show_error(title='Cannot load Gitlab (Self-Hosted) Settings', duration=6000, description=f'Failed to load, because "{str(e)}". Please try again.')
                return

    def on_auth_deeplink_received(self, url: str):
        try:
            self.client.oauth2_response(response_url=url)
            groups = self.client.get_groups()
            if not groups:
                raise Exception("Failed to load groups")
            current_group = self.client.get_current_group()
            if current_group is None:
                current_group = groups[0]
                self.client.set_current_group(current_group)
            self.show_settings_dialog(current_group, groups)
            self._setup_connected_state()
            self.is_setup = True
            self.is_setup_for_workspace = True
            self.is_connected = True
            self.start_update()
        except Exception as e:
            ap.UI().show_error(title='Gitlab (Self-Hosted) authentication failed', duration=6000, description=f'The authentication failed, because "{str(e)}". Please try again.')
            return

    def setup_create_project_dialog_entries(self, action_id, dialog: ap.Dialog):
        if action_id == create_repo_dialog_entry:
            if self.is_setup:
                dialog.add_info("You may need to <b>log into</b> Gitlab again after the final step.", var=create_dialog_info_entry)
                return [create_dialog_info_entry]
            return []

    def on_create_project_dialog_entry_selected(self, action_id: str, dialog: ap.Dialog):
        #stub
        return

    def setup_project(self, action_id: str, dialog: ap.Dialog, project_id: str, project_name: str, progress: ap.Progress):
        if action_id == create_repo_dialog_entry:
            return self.create_new_repo(project_id, project_name, progress)
        
    def validate_url(self, dialog: ap.Dialog, value: str):
        if not value or len(value) == 0:
            return "Please insert a valid url"

        url_pattern = re.compile(
            r'^(https?://)'  # scheme (http:// or https://)
            r'([a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})+|localhost)'  # Domain name or IP address
            r'(:\d+)?'  # Optional port number
            r'(/.*)?$'  # Optional path with a trailing slash
        )
        
        # Use the pattern to match the URL
        if url_pattern.match(value) == None:
            dialog.set_value(client_values_info_entry, "Please insert your valid Gitlab url first.")
            return "Please insert a valid url"
        extracted_url = self.extract_server_url(value)
        dialog.set_value(client_values_info_entry, f"Create a <a href='{extracted_url}/admin/applications/new'>Gitlab OAuth app</a> with following settings:<br><br>1. Application Name: <b>Anchorpoint</b><br>2. Redirect URI: <b>https://www.anchorpoint.app/app/integration/auth</b><br>3. Uncheck <b>Confidential</b> checkbox and check <b>Trusted</b> checkbox<br>4. Check api, read_user, read_repository, write_repository, profile and email scopes<br>5. Press <b> Save Application</b> and enter the client id below")
        return
    
    def extract_server_url(self, url: str):
        parsed_url = urlparse(url)
        return urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
    
    def update_dialog_after_validate(self, dialog: ap.Dialog, isValid: bool):
        dialog.set_enabled(connect_to_server_btn_entry, isValid)

    def validate_client_id(self, dialog: ap.Dialog, value: str):
        if not value or len(value) == 0:
            return "Please add a valid client id"
        
        import re
        client_id_pattern = re.compile(
            r'^[0-9a-f]{64}$'
        )
        if client_id_pattern.match(value) == None:
            return "Please add a client id with 64 characters"
        return
    
    def connect_to_server(self, dialog: ap.Dialog):
        dialog.set_processing(connect_to_server_btn_entry, True, "Testing connection")
        server_url = dialog.get_value(server_url_entry)
        client_id = dialog.get_value(client_id_entry)
        reachable = self.client.is_server_reachable(server_url)
        dialog.set_processing(connect_to_server_btn_entry, False)
        if reachable:
            self.client.store_for_workspace(host_url=server_url, client_id=client_id)
            self.client.setup_workspace_settings()
            ap.UI().show_success(title='Connected to Gitlab', duration=3000, description=f'You are now connected to Gitea (Self-Hosted).<br>Please continue with the authentication.')
            self.client.start_auth()
            self.start_auth()
            dialog.close()
        else:
            ap.UI().show_error(title='Cannot connect to Gitlab', duration=6000, description=f'Failed to connect to Gitea.<br>Please check your url and try again.')
            dialog.set_enabled(connect_to_server_btn_entry, False)
            return
        
    def show_workspace_setup_dialog(self):
        dialog = ap.Dialog()
        dialog.name = setup_action_id
        dialog.title = "Setup Gitlab (Self-Hosted) for Workspace"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitea/logo.svg")
        dialog.callback_validate_finsihed = self.update_dialog_after_validate

        dialog.add_text("<b>1. Gitlab URL</b>", var="remoteurltext")
        dialog.add_info("Enter your Gitlab server url with port if needed")
        dialog.add_input(placeholder='https://mygitlabserver.com:3030', var=server_url_entry, width=400, validate_callback=self.validate_url)

        dialog.add_text("<b>2. Gitea OAuth Application</b>", var="oauthapp")
        dialog.add_info("Insert your valid Gitea url first", var=client_values_info_entry)
        dialog.add_text("Client ID")
        dialog.add_input(placeholder='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', var=client_id_entry, width=400, validate_callback=self.validate_client_id)

        dialog.add_button("Connect to Gitlab", var=connect_to_server_btn_entry, callback=lambda d: self.connect_to_server(d), enabled=False)

        dialog.show()

    def change_group_callback(self, dialog: ap.Dialog, value: str, groups):
        group = next((x for x in groups if x.name == value), None)
        if group is None:
            return
        self.client.set_current_group(group)

    def credential_btn_callback(self, dialog: ap.Dialog):
        dialog.hide_row(settings_credential_btn_entry, False)
        dialog.hide_row(settings_credential_btn_highlight_entry, True)
        ctx = ap.get_context()
        ctx.run_async(setup_credentials_async, dialog, self.client.get_host_url())

    def show_settings_dialog(self, current_group, groups):
        dialog = ap.Dialog()
        dialog.name = settings_action_id
        dialog.title = "Gitlab (Self-Hosted) Settings"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitlab_self/logo.svg")

        dialog.add_text("<b>1. Account</b>", var="accounttext")
        dialog.add_text(groups[0].name)
        dialog.add_empty()

        dialog.add_text("<b>2. Group</b>", var="grouptext")

        dropdown_entries = []
        for group in groups:
            entry = ap.DropdownEntry()
            entry.name = group.name
            if group.avatar_url is not None:
                entry.icon = group.avatar_url
            else:
                entry.icon = ":/icons/organizations-and-products/gitlab.svg"
            entry.use_icon_color = True
            dropdown_entries.append(entry)

        dialog.add_dropdown(current_group.name, dropdown_entries, var=settings_group_dropdown_entry, callback=lambda d, v: self.change_group_callback(d,v, groups))
        dialog.add_info("Allow Anchorpoint to create repositories and add<br>members in a dedicated group.")
        dialog.add_empty()

        dialog.add_text("<b>3. Git Credentials</b>")
        dialog.add_image(os.path.join(self.ctx.yaml_dir, "gitlab_self/gitLabCredentials.webp"),width=230)
        dialog.add_info("Opens the Git Credential Manager, where you need to<br>enter your Gitlab login data to grant Anchorpoint<br>permission to upload and download files.")
        dialog.add_button("Enter your Gitlab credentials", var=settings_credential_btn_highlight_entry, callback=self.credential_btn_callback)
        dialog.add_button("Enter your Gitlab credentials", var=settings_credential_btn_entry, callback=self.credential_btn_callback, primary=False)
        dialog.hide_row(settings_credential_btn_entry, True)

        dialog.show()

    def show_clear_integration_dialog(self):
        dialog = ap.Dialog()
        dialog.name = clear_action_id
        dialog.title = "Disconnect Gitlab (Self-Hosted)"
        dialog.icon = os.path.join(self.ctx.yaml_dir, "gitea/logo.svg")

        dialog.add_text("Do you also want to remove the gitlab server infos (url,<br>client id) for all workspace members?")
        dialog.add_checkbox(text="Delete gitlab server infos from workspace",var=remove_data_entry, default=False)

        dialog.add_button("Disconnect", var="disconnect", callback=self.clear_integration)
        dialog.show()

    def clear_integration(self, dialog: ap.Dialog):
        remove_data = dialog.get_value(remove_data_entry)
        self.client.clear_integration(remove_data)
        self.is_setup = False
        self.is_setup_for_workspace = False
        self._setup_not_connected_state()
        self.start_update()
        dialog.close()

    def create_new_repo(self, project_id: str, project_name: str, progress: ap.Progress) -> str:
        current_group = self.client.get_current_group()
        try:
            progress.set_text("Creating Gitlab Project")
            new_repo = self.client.create_project(current_group, project_name)
            settings = aps.SharedSettings(project_id, self.ctx.workspace_id, "integration_info")
            settings.set(integration_project_name_key, new_repo.name)
            settings.store()
            
            progress.set_text("")
            if new_repo is None:
                raise Exception("Created project not found")
            return new_repo.http_url_to_repo
        except Exception as e:
            if "has already been taken" in str(e):
                ap.UI().show_error(title='Cannot create Gitlab Repository', duration=8000, description=f'Failed to create, because project with name {project_name} already exists. Please try again.')
            else:
                ap.UI().show_error(title='Cannot create Gitlab Repository', duration=8000, description=f'Failed to create, because "{str(e)}". Please try again<br>or check our <a href="https://docs.anchorpoint.app/docs/1-overview/integrations/gitlab_self">troubleshooting</a>.')
            raise e