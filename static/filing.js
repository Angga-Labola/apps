document.getElementById("form").addEventListener("submit", async(e)=>{
    e.preventDefault();
    
    const filingInputValue=document.getElementById("filingInput").value;
    const loadingText=document.getElementById("loadingText");
    const resultContainer=document.getElementById("result-container");

    loadingText.style.display = "block";

    try{
        const response=await fetch("/filing",{
            method:"POST",
            headers:{
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                "filingInput": filingInputValue
            })
        });

        if (!response.ok) throw new Error("Network response was not ok");
        
        const data= await response.json();
        const {ticker,filings} = data  
        let htmlOutput=`<div></div>`
         if (ticker) {
            htmlOutput += `<h2>Ticker: ${ticker}</h2>`;
        }
        
        if (filings && filings.length > 0) {
            // Loop through each filing inside the list
            filings.forEach(filing => {
                
                // 1. Build a sub-list of material events for this filing
                let eventsHtml = '';
                if (filing.material_events && filing.material_events.length > 0) {
                    eventsHtml += '<ul>';
                    filing.material_events.forEach(eventText => {
                        eventsHtml += `<li>${eventText}</li>`;
                    });
                    eventsHtml += '</ul>';
                } else {
                    eventsHtml = '<p>No material events noted.</p>';
                }

                // 2. Combine the date, form type, and our structured event list
                htmlOutput += `
                    <div class="filing-item" style="border-bottom: 1px solid #ccc; padding: 15px 0;">
                        <p><strong>Filing Date:</strong> ${filing.filed_date || 'N/A'}</p>
                        <p><strong>Form Type:</strong> ${filing.form_type || 'N/A'}</p>
                        <div><strong>Material Events:</strong> ${eventsHtml}</div>
                    </div>
                `;
            });
        } else if (filings) {
            htmlOutput += `<p>No filings found for this ticker.</p>`;
        }

        resultContainer.innerHTML=htmlOutput
    } 
    
    catch(error){
        alert("Error entering ticker: " + error.message);
    }

    finally{
        loadingText.style.display="none";
    }


        
    
})