function discardAccountChanges() {
    window.onbeforeunload = null;
    document.getElementById("actionButtons").style.display = "none";
    document.getElementById("accountDetailsForm").reset();
};

function accountDetailsChanged() {
    window.onbeforeunload = function () {
        return true;
    };
    document.getElementById("actionButtons").style.display = "block";
};

function submitAccountChanges() {
    window.onbeforeunload = null;
    document.getElementById("accountDetailsForm").submit();
};
