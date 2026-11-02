
document.getElementById('form').addEventListener('submit', async (e) => {
    
    e.preventDefault(); 
        
    const urlInputValue = document.getElementById('urlInput').value;
    const loadingText = document.getElementById('loadingText');
    const container = document.getElementById('result-container');
        
    loadingText.style.display = 'block';
    

    try {
        const response = await fetch('/url-locator', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    urlInput: urlInputValue
                })
            });

        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        const {country, region, city, isp, url} = data
        
        let htmlOutput='<div></div>';
        if (country){
            htmlOutput += `<p>Country: ${country}</p>`
        }

        if (region){
            htmlOutput += `<p>Region: ${region}</p>`
        }

        if (city){
            htmlOutput += `<p>City: ${city}</p>`
        }

        if (isp){
            htmlOutput += `<p>isp: ${isp}</p>`
        }

        if (url){
            htmlOutput += `<p>url: ${url}</p>`
        }
        
        
        container.innerHTML = htmlOutput; 
        
    } catch (error) {
        alert('Error entering url: ' + error.message);
    } finally {
        loadingText.style.display = 'none';
    }
});
