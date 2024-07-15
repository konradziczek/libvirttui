/* g++ fix_vnc.cpp -o fix_vnc */

#include <iostream>
#include <fcntl.h>
#include <unistd.h>
#include <sstream>
#include <pwd.h>
#include <grp.h>
#include <filesystem>

int main(int argc, char **argv)
{
    if (argc != 3) {
        fprintf(stderr, "Usage: ./fix_vnc <username> <vm_name>\n");
        exit(1);
    }

    struct passwd *pwd_new = getpwnam(std::string(argv[1]).c_str());
    if (pwd_new == NULL) {
        fprintf(stderr, "User %s does not exist.\n", argv[1]);
        exit(1);
    }

    struct group *grp_new = getgrnam("qemu");
    if (grp_new == NULL) {
        fprintf(stderr, "Group %s does not exist.\n", argv[1]);
        exit(1);
    }

    std::string home_libvirttui_dir_path = "/tmp/libvirttui_" + std::to_string((unsigned int)pwd_new->pw_uid) + "/vm__" + std::string(argv[2]) + ".vnc.sock";

    printf(("Fixing " + home_libvirttui_dir_path + "...\n").c_str());

    chown(home_libvirttui_dir_path.c_str(), pwd_new->pw_uid, grp_new->gr_gid);

    printf("Done.\n");
}
