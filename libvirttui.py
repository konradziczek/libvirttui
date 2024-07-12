#!/opt/libvirttui/venv/bin/python

import os
import sys
import time
import json
import re
import subprocess
import pwd
import psutil
import libvirt
from filelock import Timeout, FileLock
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Grid
from textual.widgets import Header, Footer, Static, Label, Button, ListItem, ListView
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.events import Mount
from textual.message import Message
from textual.reactive import reactive
from textual.css.query import NoMatches
from rich.console import RenderableType
from rich.text import Text as RichText
from rich.style import Style as RichStyle
from rich.table import Table as RichTable


SCRIPT_FILE_PATH = os.path.abspath(__file__)
SCRIPT_DIR_PATH = os.path.dirname(SCRIPT_FILE_PATH)
VIRT_DATA_DIR_PATH = "/opt/virt_data"

DOMAIN_MEMBERS_ONLY = True

DOMAIN_STATES = {
    libvirt.VIR_DOMAIN_NOSTATE: "VM no state",
    libvirt.VIR_DOMAIN_RUNNING: "VM running",
    libvirt.VIR_DOMAIN_BLOCKED: "VM idle",
    libvirt.VIR_DOMAIN_PAUSED: "VM paused",
    libvirt.VIR_DOMAIN_SHUTDOWN: "VM in shutdown",
    libvirt.VIR_DOMAIN_SHUTOFF: "VM shut off",
    libvirt.VIR_DOMAIN_CRASHED: "VM crashed",
    libvirt.VIR_DOMAIN_PMSUSPENDED: "VM pm suspended"
}

if (-1000 in DOMAIN_STATES):
    print("State -1000 exists.")
    exit(1000)
else:
    libvirt.VIR_DOMAIN_NOTEXIST = -1000
    DOMAIN_STATES[libvirt.VIR_DOMAIN_NOTEXIST] = "VM not exist"


class MessageScreen(ModalScreen):
    TYPE_TEXTONLY = 1
    TYPE_OK = 2
    TYPE_CONFIRM = 3

    def __init__(self, screen_type, *args, **kwargs):
        self.screen_type = screen_type
        super().__init__(*args, **kwargs)


    def compose(self) -> ComposeResult:
        if self.screen_type == self.TYPE_TEXTONLY:
            yield Grid(
                Label("", id="message-window-content"),
                id="message-window-textonly",
            )
        elif self.screen_type == self.TYPE_OK:
            yield Grid(
                Label("", id="message-window-content"),
                Static(),
                Button("Close", variant="default", id="button-close"),
                Static(),
                id="message-window-ok",
            )
        elif self.screen_type == self.TYPE_CONFIRM:
            yield Grid(
                Label("", id="message-window-content"),
                Static(),
                Button("OK", variant="primary", id="button-ok"),
                Static(),
                Button("Cancel", variant="default", id="button-cancel"),
                Static(),
                id="message-window-confirm",
            )
        else:
            raise Exception("ERROR: Incorrect screen type.")


    class ImagesRefreshRequired(Message):
        def __init__(self) -> None:
            super().__init__()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "button-cancel" or event.button.id == "button-close":
            self.app.pop_screen()
        self.app.post_message(self.app.ImagesRefreshRequired())


    def set_content(self, content):
        self.app.query_one("#message-window-content").update(content)



class ImageListView(ListView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    class Highlighted(ListView.Highlighted):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)


    class ImagesRefreshRequired(Message):
        def __init__(self) -> None:
            super().__init__()


    def on_mount(self, event: Mount) -> None:
        self.post_message(self.ImagesRefreshRequired())



class ImageListItem(ListItem):
    def __init__(self, image_key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_key = image_key



class ImageDetails(Container):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.styles.overflow_y = "auto"


    def render_details(self, image):
        self.remove_children()
        if image:
            self.mount(Static(f"{image['name']}\n", id="image-details-title"))

            if image['state'] == libvirt.VIR_DOMAIN_RUNNING:
                state_container = Horizontal(
                    Static("State:", classes="image-details-first-column"),
                    Static(
                        f"{DOMAIN_STATES[image['state']]} :smiling_face_with_smiling_eyes:\n",
                        id="state-running"
                    ),
                    classes="details-row"
                )
            else:
                state_container = Horizontal(
                    Static("State:", classes="image-details-first-column"),
                    Static(
                        f"{DOMAIN_STATES[image['state']]}\n",
                        id="state-not-running"
                    ),
                    classes="details-row"
                )
            self.mount(state_container)

            self.mount(
                Horizontal (
                    Static("vCPU count:", classes="image-details-first-column"),
                    Static(str(image['cpu_count'])),
                    classes="details-row"
                )
            )
            self.mount(
                Horizontal (
                    Static("Memory:", classes="image-details-first-column"),
                    Static(f"{image['memory']} MB"),
                    classes="details-row"
                )
            )

            self.mount(Static(f"------------------------"))

            self.mount(Static(f"Description:\n{image['description']}\n"))



class LibvirtTuiApp(App):
    CSS_PATH = "libvirttui.tcss"

    def __init__(self, user_id, user_name, user_domain, user_home_dir_path, libvirt_conn, images, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = str(user_id)
        self.user_name = user_name
        self.user_domain = user_domain
        self.user_home_dir_path = user_home_dir_path
        self.vm_dir = os.path.join(VIRT_DATA_DIR_PATH, "vm", user_id)
        self.images_dir = os.path.join(VIRT_DATA_DIR_PATH, "images")
        self.libvirt_conn = libvirt_conn
        self.images = images
        self.current_image_key = None

        with open('/proc/cpuinfo') as f:
            cpu_info = f.read()
        self.cpu_count = cpu_info.count('processor')

        try:
            mem_info = psutil.virtual_memory()
        except Exception as e:
            return f"Błąd: {e}"
        self.memory = int(mem_info.total / (1024 ** 2))  # Bajty do megabajtów

        self.cpu_usage = 0
        self.memory_usage = 0

        for k, v in self.images.items():
            self.images[k]['state'] = libvirt.VIR_DOMAIN_NOTEXIST


    class ImagesRefreshRequired(Message):
        def __init__(self) -> None:
            super().__init__()


    def update_images(self):
        for k, v in self.images.items():
            self.images[k]['state'] = libvirt.VIR_DOMAIN_NOTEXIST

        try:
            domains = self.libvirt_conn.listAllDomains(0)
        except:
            domains = []

        suffix = f"_{self.user_id}"
        for domain in domains:
            if domain.name().startswith("libvirttui_") and domain.name().endswith(suffix):
                domain_base_name = (domain.name())[11:-len(suffix)] # libvirttui_ has 11 characters
                if domain_base_name in self.images:
                    info = domain.info()
                    self.images[domain_base_name]['state'] = info[0]

        list_view = self.query_one(ImageListView)

        index_backup = list_view.index
        if not index_backup:
            index_backup = 0
        list_view.clear()
        images_list = []
        self.cpu_usage = 0
        self.memory_usage = 0
        for key, image in self.images.items():
            if image['state'] == libvirt.VIR_DOMAIN_RUNNING:
                images_list.append(ImageListItem(key, Label(f":green_circle: {image['name']}")))
            else:
                images_list.append(ImageListItem(key, Label(f":white_circle: {image['name']}")))

            if image['state'] != libvirt.VIR_DOMAIN_NOTEXIST and image['state'] != libvirt.VIR_DOMAIN_SHUTOFF:
                self.cpu_usage = self.cpu_usage + image['cpu_count']
                self.memory_usage = self.memory_usage + image['memory']

        self.additional_info.update(
            f"VM vCPUs usage: {self.cpu_usage} / {self.cpu_count} " \
            f"| VM RAM usage: {self.memory_usage} / {self.memory} MB"
        )

        list_view.extend(images_list)
        list_view.index = index_backup




    def set_footer_bindings(self, image_key):
        self._bindings.keys = {}

        if image_key:
            if self.images[image_key]['state'] == libvirt.VIR_DOMAIN_RUNNING:
                self.bind(keys="s", action="stop_vm", description="Stop VM")
            else:
                self.bind(keys="s", action="start_vm", description="Start VM")

        self.bind(keys="q,ctrl+c", action="quit", description="Quit the app")

        self.footer._key_text = None
        self.footer.refresh()


    def compose(self) -> ComposeResult:

        with Container(id="app"):
            with Container(id="title-bar"):
                yield Static(
                    ":hammer_and_wrench: VM management interface",
                    id="title"
                )

            list_view = ImageListView(id="images-list")
            self.set_focus(list_view)
            yield list_view

            yield ImageDetails(id="image-details")

            self.additional_info = Static("", id="additional_info")
            yield self.additional_info

        self.footer = CustomFooter()
        yield self.footer


    def action_start_vm(self):
        self.start_vm()


    def action_stop_vm(self):
        self.stop_vm()


    @work(exclusive=True, thread=True)
    def start_vm(self):
        image = self.images[self.current_image_key]

        image_path = os.path.join(self.images_dir, image['image_file'])
        vm_name = f"libvirttui_{self.current_image_key}_{self.user_id}"
        vm_path = os.path.join(self.vm_dir, f"{self.current_image_key}.qcow2")

        self.call_from_thread(self.push_screen, MessageScreen(MessageScreen.TYPE_TEXTONLY))

        try:
            domain = self.libvirt_conn.lookupByName(vm_name)
        except libvirt.libvirtError:
            domain = None

        if not domain:

            if not os.path.isfile(vm_path):

                self.call_from_thread(self.screen.set_content, f"Cloning virtual machine image...")

                time.sleep(2);

                if not os.path.isfile(image_path):
                    return self.thread_pop_screen_push_message_ok(f"ERROR: Image '{self.current_image_key}' not found.")

                standard_copy_required = False
                try:
                    command = f'cp --reflink=always {image_path} {vm_path}'
                    cmd = subprocess.run(
                        command, check=True, text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                except subprocess.CalledProcessError as e:
                    if "Operation not supported" in e.stderr:
                        standard_copy_required = True
                    else:
                        return self.thread_pop_screen_push_message_ok(
                            f"ERROR: Cannot clone virtual machine image ({e.stderr})."
                        )

                if standard_copy_required:
                    self.call_from_thread(self.screen.set_content,
                        f"Reflinking not supported. Cloning virtual machine image in a classic way (it may be slow)..."
                    )
                    try:
                        command = f'cp --sparse=always {image_path} {vm_path}'
                        cmd = subprocess.run(
                            command, check=True, text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                        )
                    except subprocess.CalledProcessError as e:
                        return self.thread_pop_screen_push_message_ok("ERROR: Cannot clone virtual machine image.")

            self.call_from_thread(self.screen.set_content, f"Creating virtual machine in hypervisor...")
            fp = open(os.path.join(SCRIPT_DIR_PATH, "templates", image['template_file']), "r")
            xmldesc = fp.read()
            fp.close()

            vm_mounts = ""
            if image['mounts']:
                for k, v in image['mounts'].items():
                    socket_path = f"/tmp/libvirttui_{self.user_id}/vm__{self.current_image_key}__{k}.sock"
                    vm_mounts = f"""{vm_mounts}
                        <filesystem type="mount" accessmode="passthrough">
                        <driver type="virtiofs" queue="1024"/>
                        <source socket="{socket_path}"/>
                        <target dir="{k}"/>
                        </filesystem>
                    """

            vnc_socket = f"/tmp/libvirttui_{self.user_id}/vm__{self.current_image_key}.vnc.sock"

            xmldesc = xmldesc.replace('$TEMPLATE_VM_NAME$', vm_name)
            xmldesc = xmldesc.replace('$TEMPLATE_VM_PATH$', vm_path)
            xmldesc = xmldesc.replace('$TEMPLATE_VM_CPU_COUNT$', str(image['cpu_count']))
            xmldesc = xmldesc.replace('$TEMPLATE_VM_MEMORY$', str(image['memory']))
            xmldesc = xmldesc.replace('$TEMPLATE_VM_MOUNTS$', vm_mounts)
            xmldesc = xmldesc.replace('$TEMPLATE_VM_VNC_SOCKET$', vnc_socket)
            xmldesc = xmldesc.replace('$TEMPLATE_USER_NAME$', self.user_name)

            time.sleep(2);

            domain = self.libvirt_conn.defineXML(xmldesc)
            if not domain:
                return self.thread_pop_screen_push_message_ok(
                    f"ERROR: Cannot create virtual machine '{image['name']} ({self.current_image_key})' in hypervisor."
                )

        elif domain.info()[0] != libvirt.VIR_DOMAIN_SHUTOFF:

            return self.thread_pop_screen_push_message_ok((
                f"ERROR: Virtual machine '{image['name']} ({self.current_image_key})' "
                f"is already running or is in intermediate state."
            ))

        if image['mounts']:
            self.call_from_thread(self.screen.set_content, f"Starting virtiofsd services...")
            for k, v in image['mounts'].items():
                username_long = f"{self.user_name}@{self.user_domain}" if self.user_domain else self.user_name
                mount_path = v
                mount_path = mount_path.replace('<username_short>', self.user_name)
                mount_path = mount_path.replace('<username_long>', username_long)
                try:
                    command = f"{os.path.join(SCRIPT_DIR_PATH, 'start_virtiofsd')} " \
                              f"'{username_long}' '{self.user_home_dir_path}' " \
                              f"'{self.current_image_key}' '{k}' '{mount_path}'"
                    cmd = subprocess.run(
                        command, check=True, text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                except subprocess.CalledProcessError as e:
                    return self.thread_pop_screen_push_message_ok((
                        f"ERROR: Cannot setup virtiofsd mount (name: {k}, code: {e.returncode})."
                    ))

        self.call_from_thread(self.screen.set_content, f"Virtual machine is being turned on...")

        time.sleep(1)

        try:
            domain.create()
        except libvirt.libvirtError as e:
            return self.thread_pop_screen_push_message_ok(
                f"ERROR: An error occured while creating virtual machine " \
                f"'{image['name']} ({self.current_image_key})': {e}"
            )

        time.sleep(5)

        state, reason = domain.state()

        if state == libvirt.VIR_DOMAIN_RUNNING:
            return self.thread_pop_screen_push_message_ok(
                f"Virtual machine '{image['name']} ({self.current_image_key})' has been turned on."
            )
        else:
            return self.thread_pop_screen_push_message_ok(
                f"ERROR: Virtual machine '{image['name']} ({self.current_image_key})' cannot be turned on."
            )


    @work(exclusive=True, thread=True)
    def stop_vm(self):
        self.call_from_thread(self.push_screen, MessageScreen(MessageScreen.TYPE_TEXTONLY))
        self.call_from_thread(self.screen.set_content, "Stopping virtual machine... Please, wait 15 seconds.")

        image = self.images[self.current_image_key]

        vm_name = f"libvirttui_{self.current_image_key}_{self.user_id}"

        try:
            domain = self.libvirt_conn.lookupByName(vm_name)
        except libvirt.libvirtError:
            return self.thread_pop_screen_push_message_ok(
                f"ERROR: Virtual machine '{image['name']} ({self.current_image_key})' not found in hypervisor."
            )

        state, reason = domain.state()

        if state != libvirt.VIR_DOMAIN_RUNNING:
            return self.thread_pop_screen_push_message_ok(
                f"ERROR: Virtual machine '{image['name']} ({self.current_image_key})' is not running."
            )

        domain.shutdown()
        time.sleep(15);

        state, reason = domain.state()

        if state == libvirt.VIR_DOMAIN_RUNNING:
            self.call_from_thread(self.screen.set_content, "Still running! Time for ungraceful kill...")
            domain.destroy()
            time.sleep(5)
            state, reason = domain.state()

        if state != libvirt.VIR_DOMAIN_RUNNING:
            return self.thread_pop_screen_push_message_ok(
                f"Virtual machine '{image['name']} ({self.current_image_key})' has been turned off."
            )
        else:
            return self.thread_pop_screen_push_message_ok(
                f"ERROR: Virtual machine '{image['name']} ({self.current_image_key})' cannot be turned off."
            )


    def thread_pop_screen_push_message_ok(self, content) -> None:
        self.call_from_thread(self.pop_screen)
        self.call_from_thread(self.push_screen, MessageScreen(MessageScreen.TYPE_OK))
        self.call_from_thread(self.screen.set_content, content)
        return None


    def on_libvirt_tui_app_images_refresh_required(self, event: ImagesRefreshRequired) -> None:
        self.update_images()


    def on_image_list_view_images_refresh_required(self, event: ImageListView.ImagesRefreshRequired) -> None:
        self.update_images()


    def on_image_list_view_highlighted(self, event: ImageListView.Highlighted) -> None:
        if event.list_view.highlighted_child:
            image_key = event.list_view.highlighted_child.image_key
            self.set_footer_bindings(image_key)
            self.query_one("#image-details").render_details(self.images[image_key])
        else:
            image_key = None
            self.set_footer_bindings(None)
            self.query_one("#image-details").render_details(None)

        self.current_image_key = image_key



class CustomFooter(Footer):
    def render(self) -> RenderableType:
        result = super().render()

        table = RichTable(show_header=False, show_edge=False, box=None, expand=True)
        table.add_column(justify="left")
        table.add_column(justify="right")
        table.add_row(result, RichText("Licensed under the GPL v3, K. Zaworski", RichStyle(color="#00ccff")))

        return table



if __name__ == "__main__":
    if len(sys.argv) == 2:
        pattern = r'^[0-9]+$'
        if sys.argv[1].isdigit() and re.match(pattern, sys.argv[1]):
            user_id = sys.argv[1].strip()
        else:
            print("Given argument should be numerical.")
            exit(1)
    else:
        print("Exactly one argument should be given.")
        exit(1)

    try:
        user_name = pwd.getpwuid(int(user_id)).pw_name
        user_home_dir_path = pwd.getpwuid(int(user_id)).pw_dir
    except KeyError:
        print(f"ERROR: Cannot get username and home directory path for uid {user_id}.")
        exit(1)

    user_domain = None

    if user_name.count("@") > 0:
        if (user_name.count("@") == 1
            and user_name.split("@")[0]
            and user_name.split("@")[-1]
            and "." in user_name.split("@")[-1]
        ):
            user_domain = user_name.split("@")[-1]
            user_name = user_name.split("@")[0]
        else:
            print("ERROR: Incorrect domain member username.")
            exit(1)

    if DOMAIN_MEMBERS_ONLY and not user_domain:
        print("ERROR: Only domain members are allowed to run this program.")
        exit(1)

    script_lock = FileLock(os.path.join(SCRIPT_DIR_PATH, "libvirttui.lock"))
    try:
        script_lock.acquire(blocking=False)
    except Timeout:
        print("ERROR: Another instance of this application is currently running.")
        exit(1)

    if not os.path.exists(os.path.join(VIRT_DATA_DIR_PATH, "images")):
        print(f"ERROR: Path {os.path.join(VIRT_DATA_DIR_PATH, 'images')} does not exist.")
        exit(1)

    if not os.path.exists(os.path.join(VIRT_DATA_DIR_PATH, "vm")):
        print(f"ERROR: Path {os.path.join(VIRT_DATA_DIR_PATH, 'vm')} does not exist.")
        exit(1)

    vm_dir = os.path.join(VIRT_DATA_DIR_PATH, "vm", user_id)

    if not os.path.exists(vm_dir):
        os.makedirs(vm_dir)

    os.chmod(vm_dir, 0o2770)

    libvirt_conn = libvirt.open("qemu:///system")
    if not libvirt_conn:
        print("ERROR: Failed to open connection to qemu.")
        exit(1)

    images = None

    try:
        with open(os.path.join(VIRT_DATA_DIR_PATH, "images.json"), 'r') as file:
            images = dict(json.load(file))['images']
    except FileNotFoundError:
        print(f"Error: File images.json not found.")
        exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding images JSON: {e}")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading images.json file: {e}")
        exit(1)

    if not images:
        print("There are no virtual machine images available.")
        exit()

    app = LibvirtTuiApp(user_id, user_name, user_domain, user_home_dir_path, libvirt_conn, images)
    app.run()
