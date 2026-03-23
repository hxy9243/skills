module.exports = {
  launch_options: {
    args: ["--no-sandbox", "--disable-setuid-sandbox"]
  },
  pdf_options: {
    displayHeaderFooter: true,
    margin: {
      top: "20mm",
      bottom: "20mm"
    },
    headerTemplate: "<style>#header, #footer { padding: 0 !important; }</style><div style='font-size: 8px; color: #708090; width: calc(100% - 80px); margin: 0 40px; padding-bottom: 10px; padding-top: 10px;'>Startup Researcher Intelligence Report</div>",
    footerTemplate: `<div style='font-size: 8px; color: #708090; width: calc(100% - 80px); margin: 0 40px; padding-top: 10px; padding-bottom: 10px; border-top: 1px solid #d3d3d3;'><span style='float: left;'>Generated with <a href="https://github.com/hxy9243/skills/tree/main/startup-researcher" style="color: #708090; text-decoration: none;">startup researcher</a></span><span style='float: right;'>${new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric' }).format(new Date())}</span></div>`
  }
};
