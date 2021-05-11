# List of Publications

{% for publication in publications %}
- {{publication.authors_str}}: [**{{publication.title}}**]({{publication.url}}), {{publication.venue}} **{{publication.year}}** {% if publication.type == "informal" %}*preprint* {% endif %}[dblp](https://dblp.uni-trier.de/{{publication.dblp_url}}) {{publication.public_comment}} <!-- {{publication.dblp_key}} -->
{% endfor %}
