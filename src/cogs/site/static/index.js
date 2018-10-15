function profile(guild_id){
    var xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            console.log(this.responseText);
            document.getElementById("main").innerHTML = this.responseText;
        }
    }
    xhttp.open("GET", "profile/" + guild_id, true);
    xhttp.send();
}
