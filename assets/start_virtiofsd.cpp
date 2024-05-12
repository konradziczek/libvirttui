/* g++ start_virtiofsd.cpp -o start_virtiofsd */

#include <iostream>
#include <fcntl.h>
#include <unistd.h>
#include <sstream>
#include <pwd.h>
#include <grp.h>
#include <sys/wait.h>
#include <filesystem>


namespace fs = std::filesystem;


int main(int argc, char **argv)
{
    if (argc != 6) {
        fprintf(stderr, "Usage: ./start_virtiofsd <username> <home_path> <vm_name> <share_name> <share_path>\n");
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

    if (setresgid(grp_new->gr_gid, grp_new->gr_gid, grp_new->gr_gid) != 0) {
        fprintf(stderr, "Cannot set new gid.\n");
        exit(1);
    }

    if (setresuid(pwd_new->pw_uid, pwd_new->pw_uid, pwd_new->pw_uid) != 0) {
        fprintf(stderr, "Cannot set new uid.\n");
        exit(1);
    }

    std::string home_libvirttui_dir_path = "/tmp/libvirttui_" + std::to_string((unsigned int)pwd_new->pw_uid);

    if (!fs::exists(home_libvirttui_dir_path)) {
        fs::create_directory(home_libvirttui_dir_path);
        fs::permissions(home_libvirttui_dir_path, fs::perms::owner_all | fs::perms::group_all, fs::perm_options::replace);
    }

    pid_t pid = fork();

    if (pid == -1) {
        fprintf(stderr, "Fork failed.\n");
        exit(1);
    } else if (pid == 0) {
        int fd = open((home_libvirttui_dir_path + "/vm__" + std::string(argv[3]) + "__" + std::string(argv[4]) + ".log").c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0750);
        dup2(fd, STDOUT_FILENO);
        dup2(fd, STDERR_FILENO);
        if (execl(
                "/usr/bin/flock",
                "/usr/bin/flock",
                "-n", (home_libvirttui_dir_path + "/vm__" + std::string(argv[3]) + "__" + std::string(argv[4]) + ".lockfile").c_str(),
                "/usr/local/bin/virtiofsd",
                "--shared-dir", std::string(argv[5]).c_str(),
                "--thread-pool-size", "64",
                "--socket-path", (home_libvirttui_dir_path + "/vm__" + std::string(argv[3]) + "__" + std::string(argv[4]) + ".sock").c_str(),
                "--socket-group", "qemu",
                "--sandbox", "none",
                (char*) NULL
            ) == -1
        ) {
            fprintf(stderr, "Execl error.\n");
            exit(1);
        }
    } else {
        fprintf(stdout, "Done.\n");
        exit(0);
    }

    return 0;
}
