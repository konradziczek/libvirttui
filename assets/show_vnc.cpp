/* g++ show_vnc.cpp -o show_vnc */

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
        fprintf(stderr, "Usage: ./show_vnc <username> <vm_name>\n");
        exit(1);
    }

    uid_t uid = getuid();
    uid_t euid = geteuid();
    uid_t gid = getgid();
    uid_t egid = getegid();

    if (std::string(argv[2]).find('/') != std::string::npos || std::string(argv[2]).find("..") != std::string::npos) {
        fprintf(stderr, "ERROR: Incorrect vm name.");
        exit(1);
    }

    struct passwd *pwd_new = getpwnam(std::string(argv[1]).c_str());
    if (pwd_new == NULL) {
        fprintf(stderr, "ERROR: User %s does not exist.\n", argv[1]);
        exit(2);
    }

    struct group *grp_new = getgrnam(std::string(argv[1]).c_str());
    if (grp_new == NULL) {
        fprintf(stderr, "ERROR: Group %s does not exist.\n", argv[1]);
        exit(3);
    }

    if (setresgid(grp_new->gr_gid, grp_new->gr_gid, grp_new->gr_gid) != 0) {
        fprintf(stderr, "Cannot change gid (started this program as uid: %d, effective uid: %d, gid: %d, effective gid: %d).\n", uid, euid, gid, egid);
        exit(1);
    }

    if (setresuid(pwd_new->pw_uid, pwd_new->pw_uid, pwd_new->pw_uid) != 0) {
        fprintf(stderr, "Cannot change uid (started this program as uid: %d, effective uid: %d, gid: %d, effective gid: %d).\n", uid, euid, gid, egid);
        exit(1);
    }

    std::string vnc_socket_path = "/tmp/libvirttui_" + std::to_string((unsigned int)pwd_new->pw_uid) + "/vm__" + std::string(argv[2]) + ".vnc.sock";

    if (execl("/usr/bin/vncviewer", "/usr/bin/vncviewer", vnc_socket_path.c_str(), (char*) NULL) == -1) {
        fprintf(stderr, "Execl error.\n");
        exit(1);
    }

    printf("Done.\n");
}
