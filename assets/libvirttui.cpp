/* g++ libvirttui.cpp -o libvirttui */

#include <unistd.h>
#include <sstream>
#include <pwd.h>
#include <grp.h>
#include <filesystem>


namespace fs = std::filesystem;


int main(int argc, char **argv)
{

    std::string uid_real = std::to_string(getuid());
    struct passwd *pwd_real = getpwuid(getuid());
    if (pwd_real == NULL) {
        fprintf(stderr, "Cannot get real username.\n");
        exit(1);
    }

    struct passwd *pwd_new = getpwnam("libvirttui");
    if (pwd_new == NULL) {
        fprintf(stderr, "User libvirttui does not exist.\n");
        exit(1);
    }

    struct group *grp_new = getgrnam("libvirttui");
    if (grp_new == NULL) {
        fprintf(stderr, "Group libvirttui does not exist.\n");
        exit(1);
    }

    std::string home_libvirttui_dir_path = "/tmp/libvirttui_" + std::to_string((unsigned int)pwd_real->pw_uid);

    if (!fs::exists(home_libvirttui_dir_path)) {
        fs::create_directory(home_libvirttui_dir_path);
        fs::permissions(home_libvirttui_dir_path, fs::perms::owner_all | fs::perms::group_all, fs::perm_options::replace);
    }

    if (setresgid(grp_new->gr_gid, grp_new->gr_gid, grp_new->gr_gid) != 0) {
        fprintf(stderr, "Cannot set new gid.\n");
        exit(1);
    }

    if (setresuid(pwd_new->pw_uid, pwd_new->pw_uid, pwd_new->pw_uid) != 0) {
        fprintf(stderr, "Cannot set new uid.\n");
        exit(1);
    }

    if (execl("/opt/libvirttui/libvirttui.py", "/opt/libvirttui/libvirttui.py", uid_real.c_str(), (char*) NULL) == -1) {
        fprintf(stderr, "Execl error.\n");
        exit(1);
    }

    return 0;
}
