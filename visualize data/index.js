window.addEventListener("load", main);

var json_data;

var categories_search_list = [];

/*
    get json data from the file.
*/
function getJson(event){
    var fileToLoad = document.getElementById("jsonfile").files[0];
    var fileReader = new FileReader();
    fileReader.onload = function(fielLoadedEvent){
        try{
            json_data = JSON.parse(fielLoadedEvent.target.result);
            processJsonData(json_data);
        }
        catch(ex){
            alert('Error when trying to parse json = ' + ex);
        }
    }

    fileReader.readAsText(fileToLoad);
}


/*
    Process the json data.
*/

function processJsonData(data){
    document.getElementById("selectfile").style.display = "none";
    document.getElementById("settingPart").style.display = "block";
    var categories = getCategories(data);
    listCategories(categories);


}



/*
    Return the available categories.
*/
function getCategories(data){
    var tags = new Object();
    for(var x = 0; x < data.length; x++){
        product = data[x];
        for(var y = 0; y < product["categories"].length; y++){
            tag = product["categories"][y].trim();
            if (tag == ""){
                continue;
            }
            if (tags[tag] == undefined){
                tags[tag] = 1;
            }
            else{
                tags[tag] += 1;
            }
        }
    }

    return tags;
}


/*
    Print the tag name and their number 
*/
function listCategories(tags){
    var html_text = "<h1> Categories and count </h1>";
    for(var key of Object.keys(tags)){
        html_text += "<div class = 'tagList'>\n <span class = 'tagName'>" + key + "</span>\n" + "<span class = 'tagNumber'>" + tags[key] + "</span>" + "</div>";
    }
    document.getElementById("availableCategories").innerHTML =  html_text;
    tagnames = document.getElementsByClassName("tagName");
    for(var x = 0; x < tagnames.length; x++){
        tagnames[x].addEventListener("click", search_by_category);
    }
}

/*
    when a category is clicked then search by the category
*/
function search_by_category(event){
    tag = this.innerHTML;
    html_text = "";
    nb = 0;

    if (categories_search_list.includes(tag)){
        categories_search_list = arrayRemove(categories_search_list, tag);
        this.style.backgroundColor = "#cac9c9";
    }
    else{
        categories_search_list.push(tag);
        this.style.backgroundColor = "whitesmoke";
    }
    if (categories_search_list.length != 0){
        for(var x = 0; x < json_data.length; x++){
            product = json_data[x];
            tags = product["categories"];
            select = true;
            for(var y = 0; y < categories_search_list.length; y++){
                // it doesn't contain all selected category
                if (! tags.includes(categories_search_list[y])){
                    select = false;
                }
            }
            if (select){
                nb += 1;
                html_text += productToHtml(product, x);
            }
        }
    }

    html_text = "<h1>" + nb + " results </h1>" + html_text;
    document.getElementById("showproducts").innerHTML = html_text;
    addEventToImages();
    addEventToInput();
    addEventToSaveButton();

}


/*
    Transform the product to html
*/
function productToHtml(product, index){
    images = product["images"];
    tags = product["categories"];
    infos = product["infos"]
    html_text = "\n <div class = 'product' data-index = '" + index + "'>\n<div class = 'productTitle'>" + product["title"] + "</div>";
    html_text += "\n <div class = 'productUrl'><a href = '" + product["url"] + "' target= '_blank'>" + product["url"]+"</a></div><div class = 'productImagesDiv'>";
    for(var x = 0; x < images.length; x++){
        html_text += "<div class = 'productImage' data-removed=false ><img src = '" + images[x] + "'/><p></p></div>"; 
    }
    html_text += "</div>\n<div class = 'categoriesDiv'>";
    for(var x = 0; x < tags.length; x++){
        html_text += "<div class = 'productCategory'>" + tags[x] + "</div>\n";
    }
    html_text += "</div> \n <div class = 'infos'>";
    for(var x = 0; x < infos.length; x++){
        html_text += "<p>" + infos[x] + "</p>\n";
    }
    html_text += "<p> ===================================== </p>";

    html_text += `</div>
        <p> Category should be seperated by one space </p>
        <input type='text' class = 'changeCategory' />
        <p class = 'saveText'></p>
        <button class = 'saveChange'>Save</button>
    </div>`;
    return html_text;
}

/*
    This function will add Event listener to the product images
*/
function addEventToImages(){
    images = document.getElementsByClassName("productImage");
    for(var x = 0 ; x < images.length; x++){
        images[x].addEventListener("click", clickedImage);
    }
}

/*
    this function will add event listener to input field that will change the categories
*/
function addEventToInput(){
    inputs = document.getElementsByClassName("changeCategory");
    for(var x = 0; x < inputs.length; x++){
        inputs[x].addEventListener("keydown", updateCategories);
        inputs[x].addEventListener("keyup", updateCategories);
    }
}

/*
    This function will add event listener to the button that will save the change to the product.
*/
function addEventToSaveButton(){
    save_buttons = document.getElementsByClassName("saveChange");
    for(var x = 0; x < save_buttons.length; x++){
        save_buttons[x].addEventListener("click", saveChange);
    }
}


/*
    this function will be called when an image of product is clicked
    it will mark an image as deleted and the inverse.
*/
function clickedImage(event){
    var deleted = this.dataset.removed;
    // if not deleted then delete it
    if (deleted == "false"){
        this.dataset.removed = "true";
        this.getElementsByTagName("p")[0].innerHTML = "DELETED";
    }
    else{
        this.dataset.removed = "false";
        this.getElementsByTagName("p")[0].innerHTML = "";
    }
}

/*
    This function will be called when a letter is entered in the input field, 
    it will update the categories of the product.
*/
function updateCategories(event){
    var categoriesArea = this.parentElement.getElementsByClassName("categoriesDiv")[0];
    var text = this.value.trim();
    var html_text = "";
    if (text != ""){
        // get tags
        var tags = text.split(" ");
        for(var x = 0; x < tags.length; x++){
            html_text += "<div class = 'productCategory'>" + tags[x] + "</div>\n";
        }
        categoriesArea.innerHTML = html_text;
    }
}


/*
    this function will be called when the save change button is clicked inside the product,
    it will save the change inside the json data array.
*/
function saveChange(event){
    var product = this.parentElement;
    var index = product.dataset.index;
    var data = json_data[index]; // get the specific data
    var imageDivs = product.querySelectorAll(".productImage[data-removed = false]"); // get the images that are not removed
    var categories = product.getElementsByClassName("productCategory"); // get the category of the product
    var image_srcs = [];
    var new_cat = [];
    for(var x = 0; x < imageDivs.length; x++){
        src = imageDivs[x].getElementsByTagName("img")[0].src;
        image_srcs.push(src);
    }
    for(var x = 0; x < categories.length; x++){
        new_cat.push(categories[x].innerHTML);
    }
    data["images"] = image_srcs;
    data["categories"] = new_cat;
    json_data[index] = data;
    product.getElementsByClassName("saveText")[0].innerHTML = "Product has been saved";
    console.log(json_data[index]);
}

/*
    this function will analyse the updated json data with updated categories and images.
*/
function resetPage(){
    document.getElementById("showproducts").innerHTML = "";
    categories_search_list = [];
    processJsonData(json_data);
}

/*
    This function is to uplaod the json file that contain the json data.
*/
function saveToJson(){
    var a = document.createElement("a");
    var file = new Blob([JSON.stringify(json_data, null, 4)], {type: "text/plain"});
    a.href = URL.createObjectURL(file);
    a.download = "output.json";
    a.click();
}


/*
    Function to remove from array
*/
function arrayRemove(arr, value) { 
    return arr.filter(function(ele){ return ele != value; });
}


function main(){
    console.log("hello world");
    document.getElementById("analysefile").addEventListener("click", getJson);
    document.getElementById("resetButton").addEventListener("click", resetPage);
    document.getElementById("saveJson").addEventListener("click", saveToJson);
}