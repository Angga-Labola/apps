async function loadCOmmentary(){
const commentary = 'adam-clarke';
const book = 'GEN';
const chapter = 1;

// Get Genesis 1 from the adam-clarke commentary
const response = await fetch(`https://bible.helloao.org/api/c/${commentary}/${book}/${chapter}.json`);
const data= await response.json()
document.getElementById("content").innerHTML=JSON.stringify(data);
}

loadCOmmentary()

